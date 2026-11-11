"""Leitura do corpo JSON da requisição.

Concentra o tratamento de JSON malformado e de Content-Type errado para que
todas as rotas devolvam o mesmo erro 400 no formato padrão.
"""

from __future__ import annotations

from typing import Any

from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from app.domain.erros import ErroDeDominio


def corpo_json() -> Any:
    try:
        return _ler_json()
    except (BadRequest, UnsupportedMediaType) as erro:
        raise ErroDeDominio(
            "REQUISICAO_INVALIDA",
            "O corpo da requisição não é um JSON válido.",
            400,
        ) from erro


def _ler_json() -> Any:
    from flask import request

    return request.get_json()
