"""Tela de demonstração (HTML servido pelo Flask, sem JavaScript).

A ideia desta tela é ser o mais simples possível: formulários HTML comuns,
POST + redirect + GET e páginas separadas para editar e excluir. Nada de
`fetch`, nada de bundler, nada de estado no navegador.

Ela usa EXATAMENTE os mesmos casos de uso e repositórios da API. Se uma regra
mudar no domínio, a tela muda junto — não existe uma segunda implementação das
regras para manter em sincronia.
"""

from __future__ import annotations

from uuid import UUID

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.domain.entidades import StatusEmprestimo
from app.domain.erros import ErroDeDominio
from app.http.dependencias import Dependencias
from app.http.esquemas import (
    EsquemaNovoEmprestimo,
    EsquemaNovoLivro,
    EsquemaNovoUsuario,
    dados_novo_livro,
    dados_novo_usuario,
)
from app.http.validacao import validar
from app.use_cases.emprestar_livro import EntradaEmprestarLivro


def criar_demo(deps: Dependencias) -> Blueprint:
    bp = Blueprint("demo", __name__)

    # ------------------------------------------------------------------
    # Visão geral
    # ------------------------------------------------------------------

    @bp.get("/")
    @bp.get("/visao")
    def visao():
        livros = deps.livros.listar_com_disponibilidade()
        emprestimos = deps.emprestimos.listar_detalhados()
        atrasados = deps.emprestimos.listar_atrasados(deps.relogio.agora())

        ativos = [
            emprestimo
            for emprestimo in emprestimos
            if emprestimo.status == StatusEmprestimo.ATIVO
        ]

        return render_template(
            "visao.html",
            aba_ativa="visao",
            total_livros=len(livros),
            total_exemplares=sum(livro.exemplares_total for livro in livros),
            total_disponiveis=sum(
                livro.exemplares_disponiveis for livro in livros
            ),
            total_ativos=len(ativos),
            total_atrasados=len(atrasados),
            ultimos=emprestimos[:5],
        )

    # ------------------------------------------------------------------
    # Livros
    # ------------------------------------------------------------------

    @bp.get("/livros")
    def livros():
        return render_template(
            "livros.html",
            aba_ativa="livros",
            livros=deps.livros.listar_com_disponibilidade(),
        )

    @bp.post("/livros")
    def criar_livro():
        _executar_acao("Livro cadastrado com sucesso.")
        return redirect(url_for("demo.livros"))

    @bp.get("/livros/<uuid:livro_id>/editar")
    def editar_livro(livro_id: UUID):
        livro = deps.livros.buscar_por_id(livro_id)
        if livro is None:
            abort(404)
        return render_template(
            "livro_editar.html",
            aba_ativa="livros",
            livro=livro,
        )

    @bp.post("/livros/<uuid:livro_id>/editar")
    def salvar_livro(livro_id: UUID):
        if deps.livros.buscar_por_id(livro_id) is None:
            abort(404)

        _executar_acao("Livro atualizado com sucesso.")
        return redirect(url_for("demo.livros"))

    @bp.get("/livros/<uuid:livro_id>/excluir")
    def confirmar_exclusao_de_livro(livro_id: UUID):
        livro = deps.livros.buscar_por_id(livro_id)
        if livro is None:
            abort(404)
        return render_template(
            "confirmar_exclusao.html",
            aba_ativa="livros",
            titulo="Excluir livro",
            descricao=(
                "O livro sai do catálogo. Se ele já teve empréstimos, o "
                "histórico continua aparecendo na aba Empréstimos."
            ),
            nome=livro.titulo,
            detalhe=f"{livro.autor} • ISBN {livro.isbn}",
            acao=url_for("demo.excluir_livro", livro_id=livro_id),
            voltar=url_for("demo.livros"),
        )

    @bp.post("/livros/<uuid:livro_id>/excluir")
    def excluir_livro(livro_id: UUID):
        _executar_acao("Livro excluído do catálogo.")
        return redirect(url_for("demo.livros"))

    # ------------------------------------------------------------------
    # Usuários
    # ------------------------------------------------------------------

    @bp.get("/usuarios")
    def usuarios():
        return render_template(
            "usuarios.html",
            aba_ativa="usuarios",
            usuarios=deps.usuarios.listar(),
        )

    @bp.post("/usuarios")
    def criar_usuario():
        _executar_acao("Usuário cadastrado com sucesso.")
        return redirect(url_for("demo.usuarios"))

    @bp.get("/usuarios/<uuid:usuario_id>/editar")
    def editar_usuario(usuario_id: UUID):
        usuario = deps.usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            abort(404)
        return render_template(
            "usuario_editar.html",
            aba_ativa="usuarios",
            usuario=usuario,
        )

    @bp.post("/usuarios/<uuid:usuario_id>/editar")
    def salvar_usuario(usuario_id: UUID):
        if deps.usuarios.buscar_por_id(usuario_id) is None:
            abort(404)

        _executar_acao("Usuário atualizado com sucesso.")
        return redirect(url_for("demo.usuarios"))

    @bp.get("/usuarios/<uuid:usuario_id>/excluir")
    def confirmar_exclusao_de_usuario(usuario_id: UUID):
        usuario = deps.usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            abort(404)
        return render_template(
            "confirmar_exclusao.html",
            aba_ativa="usuarios",
            titulo="Excluir usuário",
            descricao=(
                "O usuário sai da lista. Se ele já pegou algum livro, o "
                "histórico de empréstimos continua preservado."
            ),
            nome=usuario.nome,
            detalhe=usuario.email,
            acao=url_for("demo.excluir_usuario", usuario_id=usuario_id),
            voltar=url_for("demo.usuarios"),
        )

    @bp.post("/usuarios/<uuid:usuario_id>/excluir")
    def excluir_usuario(usuario_id: UUID):
        _executar_acao("Usuário excluído da lista.")
        return redirect(url_for("demo.usuarios"))

    # ------------------------------------------------------------------
    # Empréstimos
    # ------------------------------------------------------------------

    @bp.get("/emprestimos")
    def emprestimos():
        livros = deps.livros.listar_com_disponibilidade()
        return render_template(
            "emprestimos.html",
            aba_ativa="emprestimos",
            emprestimos=deps.emprestimos.listar_detalhados(),
            livros=livros,
            livros_disponiveis=[
                livro for livro in livros if livro.exemplares_disponiveis > 0
            ],
            usuarios=deps.usuarios.listar(),
        )

    @bp.post("/emprestimos")
    def criar_emprestimo():
        _executar_acao("Empréstimo registrado com sucesso.")
        return redirect(url_for("demo.emprestimos"))

    @bp.post("/emprestimos/<uuid:emprestimo_id>/devolucao")
    def devolver(emprestimo_id: UUID):
        _executar_acao("Devolução registrada com sucesso.")
        destino = request.form.get("voltar") or url_for("demo.emprestimos")
        return redirect(destino)

    # ------------------------------------------------------------------
    # Atrasados
    # ------------------------------------------------------------------

    @bp.get("/atrasados")
    def atrasados():
        return render_template(
            "atrasados.html",
            aba_ativa="atrasados",
            emprestimos=deps.emprestimos.listar_atrasados(
                deps.relogio.agora()
            ),
        )

    # ------------------------------------------------------------------
    # Execução das ações comuns
    # ------------------------------------------------------------------

    def _executar_acao(mensagem_de_sucesso: str) -> bool:
        """Executa a ação pedida pelo formulário e devolve True se deu certo.

        Toda a tela passa por aqui: valida os campos do formulário, chama o
        caso de uso e traduz erros de negócio em mensagens amigáveis. Assim
        não existe uma regra de validação diferente da API.
        """
        try:
            _despachar()
        except ErroDeDominio as erro:
            flash(_mensagem_do_dominio(erro), "erro")
            return False
        except ValidationError as erro:
            flash(_mensagem_de_validacao(erro), "erro")
            return False
        except IntegrityError:
            flash(_mensagem_de_conflito(), "erro")
            return False

        flash(mensagem_de_sucesso, "sucesso")
        return True

    def _despachar() -> None:
        rota = request.endpoint

        if rota == "demo.criar_livro":
            deps.livros.criar(_livro_do_formulario())
        elif rota == "demo.salvar_livro":
            deps.atualizar_livro.executar(
                _uuid_do_caminho("livro_id"), _livro_do_formulario()
            )
        elif rota == "demo.excluir_livro":
            deps.excluir_livro.executar(_uuid_do_caminho("livro_id"))
        elif rota == "demo.criar_usuario":
            deps.usuarios.criar(_usuario_do_formulario())
        elif rota == "demo.salvar_usuario":
            deps.atualizar_usuario.executar(
                _uuid_do_caminho("usuario_id"), _usuario_do_formulario()
            )
        elif rota == "demo.excluir_usuario":
            deps.excluir_usuario.executar(_uuid_do_caminho("usuario_id"))
        elif rota == "demo.criar_emprestimo":
            dados = validar(
                EsquemaNovoEmprestimo,
                {
                    "livro_id": request.form.get("livro_id", ""),
                    "usuario_id": request.form.get("usuario_id", ""),
                },
            )
            deps.emprestar_livro.executar(
                EntradaEmprestarLivro(
                    livro_id=dados.livro_id,
                    usuario_id=dados.usuario_id,
                )
            )
        elif rota == "demo.devolver":
            deps.devolver_emprestimo.executar(
                _uuid_do_caminho("emprestimo_id")
            )
        else:  # pragma: no cover - proteção contra rota nova sem ação
            raise RuntimeError(f"Ação não implementada para {rota}")

    return bp


# ---------------------------------------------------------------------------
# Leitura do formulário
# ---------------------------------------------------------------------------


def _uuid_do_caminho(nome: str) -> UUID:
    """O conversor `<uuid:...>` já entrega um UUID; devolvemos como está."""
    return UUID(str(request.view_args[nome]))


def _livro_do_formulario():
    dados = validar(
        EsquemaNovoLivro,
        {
            "titulo": request.form.get("titulo", ""),
            "autor": request.form.get("autor", ""),
            "isbn": request.form.get("isbn", ""),
            "exemplares_total": request.form.get("exemplares", ""),
        },
    )
    return dados_novo_livro(dados)


def _usuario_do_formulario():
    dados = validar(
        EsquemaNovoUsuario,
        {
            "nome": request.form.get("nome", ""),
            "email": request.form.get("email", ""),
        },
    )
    return dados_novo_usuario(dados)


def _mensagem_do_dominio(erro: ErroDeDominio) -> str:
    """Mensagem amigável para a tela.

    `DADOS_INVALIDOS` traz o detalhe por campo; os demais erros já têm uma
    mensagem pronta em português.
    """
    if erro.codigo == "DADOS_INVALIDOS" and isinstance(erro.detalhes, dict):
        problemas = [
            f"{campo}: {' '.join(str(mensagem) for mensagem in mensagens)}"
            for campo, mensagens in erro.detalhes.items()
        ]
        return "Dados inválidos. " + "; ".join(problemas)
    return str(erro)


def _mensagem_de_validacao(erro: ValidationError) -> str:
    problemas = []
    for item in erro.errors():
        campo = ".".join(str(parte) for parte in item["loc"]) or "campo"
        problemas.append(f"{campo}: {item['msg']}")
    return "Dados inválidos. " + "; ".join(problemas)


def _mensagem_de_conflito() -> str:
    if request.endpoint in {"demo.criar_livro", "demo.salvar_livro"}:
        return "Já existe um livro com este ISBN."
    return "Já existe um usuário com este e-mail."
