"""Fábrica da aplicação Flask.

Esta função é o "cabo de força" do projeto: cria engine, repositórios, casos
de uso, rotas e a tela de demonstração, e devolve o app pronto para escutar.

Ela NÃO chama `app.run()` — quem faz isso é o `python -m app` (desenvolvimento)
ou o Gunicorn (produção). Essa separação é o que permite testar a API inteira
com `app.test_client()` sem abrir uma porta de rede.
"""

from __future__ import annotations

import atexit
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml
from flask import Flask, Response, g, jsonify, redirect, request, send_file
from flask_swagger_ui import get_swaggerui_blueprint

from app.config import Configuracao, carregar_configuracao
from app.domain.relogio import Relogio, relogio_do_sistema
from app.http.api import criar_api
from app.http.dependencias import Dependencias
from app.http.erros import registrar_tratamento_de_erros
from app.infra.banco import criar_engine, criar_session_factory
from app.infra.repositorios import (
    SqlAlchemyEmprestimoRepositorio,
    SqlAlchemyLivroRepositorio,
    SqlAlchemyUsuarioRepositorio,
)
from app.observabilidade.logs import configurar_logs
from app.observabilidade.metricas import (
    criar_metricas,
    criar_registro_de_metricas,
)
from app.use_cases.atualizar_livro import AtualizarLivro
from app.use_cases.atualizar_usuario import AtualizarUsuario
from app.use_cases.devolver_emprestimo import DevolverEmprestimo
from app.use_cases.emprestar_livro import EmprestarLivro
from app.use_cases.excluir_livro import ExcluirLivro
from app.use_cases.excluir_usuario import ExcluirUsuario
from app.web.demo import criar_demo

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_DO_OPENAPI = RAIZ_DO_PROJETO / "docs" / "openapi.yaml"

ROTAS_IGNORADAS = {
    "/",
    "/API",
    "/health",
    "/API/health",
    "/metrics",
    "/API/metrics",
}


def criar_app(
    configuracao: Configuracao | None = None,
    *,
    engine=None,
    relogio: Relogio | None = None,
    prazo_em_dias: int | None = None,
    limite_de_emprestimos: int | None = None,
) -> Flask:
    configuracao = configuracao or carregar_configuracao()
    configurar_logs(configuracao.ambiente, configuracao.log_level)

    motor = engine or criar_engine(configuracao.database_url)
    if engine is None:
        # Fecha o pool quando o processo termina (não afeta o engine do teste).
        atexit.register(motor.dispose)

    sessao = criar_session_factory(motor)
    relogio = relogio or relogio_do_sistema
    prazo_em_dias = prazo_em_dias or configuracao.prazo_dias
    limite_de_emprestimos = (
        limite_de_emprestimos or configuracao.limite_emprestimos
    )

    # ------------------------------ Domínio ----------------------------------
    livros = SqlAlchemyLivroRepositorio(sessao)
    usuarios = SqlAlchemyUsuarioRepositorio(sessao)
    emprestimos = SqlAlchemyEmprestimoRepositorio(sessao)

    emprestar_livro = EmprestarLivro(
        livros,
        usuarios,
        emprestimos,
        relogio,
        prazo_em_dias,
        limite_de_emprestimos,
    )
    devolver_emprestimo = DevolverEmprestimo(emprestimos, relogio)

    # Casos de uso de manutenção dos cadastros (editar/excluir).
    atualizar_livro = AtualizarLivro(livros)
    excluir_livro = ExcluirLivro(livros, relogio)
    atualizar_usuario = AtualizarUsuario(usuarios)
    excluir_usuario = ExcluirUsuario(usuarios, relogio)

    # ------------------------- Observabilidade -------------------------------
    registro = criar_registro_de_metricas()
    metricas = criar_metricas(registro)

    deps = Dependencias(
        engine=motor,
        livros=livros,
        usuarios=usuarios,
        emprestimos=emprestimos,
        emprestar_livro=emprestar_livro,
        devolver_emprestimo=devolver_emprestimo,
        atualizar_livro=atualizar_livro,
        excluir_livro=excluir_livro,
        atualizar_usuario=atualizar_usuario,
        excluir_usuario=excluir_usuario,
        relogio=relogio,
        metricas=metricas,
        registro=registro,
    )

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = configuracao.secret_key
    app.config["APP_ENV"] = configuracao.ambiente
    app.config["PRAZO_DIAS"] = prazo_em_dias
    app.config["LIMITE_EMPRESTIMOS"] = limite_de_emprestimos
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.extensions["dependencias"] = deps
    app.extensions["engine"] = motor

    _registrar_filtros_de_template(app, deps)
    registrar_tratamento_de_erros(app)

    # ------------------------------- Rotas -----------------------------------
    app.register_blueprint(criar_api(deps))
    app.register_blueprint(criar_demo(deps))
    _registrar_documentacao(app)

    # Infraestrutura também na raiz, porque é o endereço que o Coolify usa.
    from app.http.rotas_infra import registrar_infraestrutura_na_raiz

    registrar_infraestrutura_na_raiz(app, deps)

    # Quem já conhece /docs continua funcionando: redireciona para o novo local.
    @app.get("/docs")
    def redirecionar_docs():
        return redirect("/API/docs", code=302)

    _registrar_observabilidade_http(app, deps)

    return app


# ---------------------------------------------------------------------------
# Documentação
# ---------------------------------------------------------------------------


def _registrar_documentacao(app: Flask) -> None:
    # O arquivo docs/openapi.yaml é a fonte da verdade: o Swagger UI só lê esse
    # arquivo e desenha a tela. Não geramos o contrato a partir das rotas para
    # não ter dois lugares diferentes dizendo a mesma coisa.
    @app.get("/API/openapi.yaml")
    def openapi_yaml():
        return send_file(
            CAMINHO_DO_OPENAPI,
            mimetype="application/yaml",
            as_attachment=False,
        )

    @app.get("/API/docs/json")
    def openapi_json():
        with CAMINHO_DO_OPENAPI.open("r", encoding="utf-8") as arquivo:
            contrato = yaml.safe_load(arquivo)
        return jsonify(contrato)

    swagger_bp = get_swaggerui_blueprint(
        "/API/docs",
        "/API/openapi.yaml",
        config={
            "app_name": "API de Empréstimos de Biblioteca",
            "docExpansion": "list",
            "deepLinking": True,
            "persistAuthorization": True,
        },
    )
    app.register_blueprint(swagger_bp)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def _registrar_filtros_de_template(app: Flask, deps: Dependencias) -> None:
    from app.domain.regras import (
        dias_de_atraso,
        esta_atrasado,
        inicio_do_dia,
    )

    @app.template_filter("data")
    def formatar_data(valor: datetime | None) -> str:
        if valor is None:
            return "—"
        return valor.strftime("%d/%m/%Y")

    @app.template_filter("data_hora")
    def formatar_data_hora(valor: datetime | None) -> str:
        if valor is None:
            return "—"
        return valor.strftime("%d/%m/%Y %H:%M")

    app.jinja_env.globals["esta_atrasado"] = esta_atrasado
    app.jinja_env.globals["dias_de_atraso"] = dias_de_atraso
    app.jinja_env.globals["inicio_do_dia"] = inicio_do_dia

    @app.context_processor
    def injetar_hoje():
        # `hoje` vem do relógio injetado, então a tela usa a mesma noção de
        # "agora" dos casos de uso.
        return {"hoje": deps.relogio.agora()}


# ---------------------------------------------------------------------------
# Logs e métricas por requisição
# ---------------------------------------------------------------------------


def _deve_medir(rota: str) -> bool:
    if not request.path.startswith("/API"):
        return False
    if rota.startswith("/API/docs"):
        return False
    return rota not in ROTAS_IGNORADAS


def _registrar_observabilidade_http(app: Flask, deps: Dependencias) -> None:
    @app.before_request
    def antes_da_requisicao():
        g.inicio = time.perf_counter()
        # Correlation id: se o cliente mandar x-request-id, respeitamos; senão
        # geramos um UUID. Esse id aparece em todos os logs daquela requisição.
        g.requisicao_id = request.headers.get("x-request-id") or str(uuid4())

    @app.after_request
    def depois_da_requisicao(resposta: Response) -> Response:
        resposta.headers["X-Request-Id"] = g.get("requisicao_id", "")

        rota = request.url_rule.rule if request.url_rule else request.path
        if not _deve_medir(rota):
            return resposta

        duracao_ms = (time.perf_counter() - g.inicio) * 1000

        deps.metricas.duracao_http.labels(
            metodo=request.method,
            rota=rota,
            status=str(resposta.status_code),
        ).observe(duracao_ms / 1000)

        # Log estruturado (JSON em produção): fácil de filtrar no Coolify.
        app.logger.info(
            "requisicao_concluida",
            extra={
                "requisicao_id": g.requisicao_id,
                "metodo": request.method,
                "rota": rota,
                "status": resposta.status_code,
                "duracao_ms": round(duracao_ms, 1),
            },
        )
        return resposta
