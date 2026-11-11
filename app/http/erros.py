"""Tratamento central de erros.

Ter UM lugar que decide o formato da resposta de erro é o que mantém a API
previsível. Toda rota pode simplesmente `raise` — quem responde é daqui.

Formato único:
  { "erro": { "codigo": "...", "mensagem": "...", "detalhes": ... } }
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.domain.erros import ErroDeDominio, erros

logger = logging.getLogger(__name__)


def _e_api() -> bool:
    return request.path.startswith("/API")


def _corpo_de_erro(
    codigo: str, mensagem: str, detalhes=None
) -> dict[str, object]:
    erro: dict[str, object] = {"codigo": codigo, "mensagem": mensagem}
    if detalhes is not None:
        erro["detalhes"] = detalhes
    return {"erro": erro}


def _campo_do_conflito(erro: IntegrityError) -> str:
    """Descobre qual índice único foi violado (isbn ou email)."""
    origem = getattr(erro, "orig", None)
    diagnostico = getattr(origem, "diag", None)
    nome = getattr(diagnostico, "constraint_name", None) or str(origem)
    if "isbn" in nome:
        return "isbn"
    if "email" in nome:
        return "email"
    return "campo único"


def registrar_tratamento_de_erros(app: Flask) -> None:
    @app.errorhandler(ErroDeDominio)
    def tratar_erro_de_dominio(erro: ErroDeDominio):
        return (
            jsonify(
                _corpo_de_erro(erro.codigo, str(erro), erro.detalhes)
            ),
            erro.status_code,
        )

    @app.errorhandler(ValidationError)
    def tratar_erro_de_validacao(erro: ValidationError):
        conflito = erros.dados_invalidos(erro.errors())
        return (
            jsonify(_corpo_de_erro(conflito.codigo, str(conflito))),
            conflito.status_code,
        )

    @app.errorhandler(IntegrityError)
    def tratar_conflito_de_banco(erro: IntegrityError):
        # Violação de campo único (isbn ou email repetido). O PostgreSQL
        # devolve o nome do índice; traduzimos para o vocabulário da API.
        conflito = erros.valor_ja_cadastrado(_campo_do_conflito(erro))
        return (
            jsonify(
                _corpo_de_erro(conflito.codigo, str(conflito))
            ),
            conflito.status_code,
        )

    @app.errorhandler(HTTPException)
    def tratar_erro_http(erro: HTTPException):
        # JSON malformado enviado pelo cliente.
        if erro.code == 400:
            corpo = _corpo_de_erro(
                "REQUISICAO_INVALIDA",
                "O corpo da requisição não é um JSON válido.",
            )
        elif erro.code == 404:
            corpo = _corpo_de_erro(
                "ROTA_NAO_ENCONTRADA",
                f"A rota {request.method} {request.path} não existe.",
            )
        elif erro.code == 405:
            corpo = _corpo_de_erro(
                "METODO_NAO_PERMITIDO",
                f"O método {request.method} não é permitido nesta rota.",
            )
        else:
            corpo = _corpo_de_erro(
                "ERRO_HTTP",
                erro.description or "Erro na requisição.",
            )

        if _e_api():
            return jsonify(corpo), erro.code

        # Para a tela de demonstração, devolvemos HTML em vez de JSON.
        return (
            render_template(
                "erro.html",
                codigo=erro.code,
                mensagem=corpo["erro"]["mensagem"],
            ),
            erro.code,
        )

    @app.errorhandler(Exception)
    def tratar_erro_inesperado(erro: Exception):
        # Loga com stack trace e NÃO expõe detalhe interno para o cliente.
        logger.exception("erro_nao_tratado", exc_info=erro)
        if _e_api():
            return (
                jsonify(
                    _corpo_de_erro(
                        "ERRO_INTERNO",
                        "Erro interno inesperado. Tente novamente mais tarde.",
                    )
                ),
                500,
            )
        return (
            render_template(
                "erro.html",
                codigo=500,
                mensagem="Erro interno inesperado. Tente novamente mais tarde.",
            ),
            500,
        )
