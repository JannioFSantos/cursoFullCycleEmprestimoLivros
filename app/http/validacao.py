"""Validação de entrada com Pydantic.

Se falhar, lança DADOS_INVALIDOS (400) já com o detalhe por campo. Assim o
cliente recebe algo como:

  { "erro": { "codigo": "DADOS_INVALIDOS",
              "detalhes": { "email": ["value is not a valid email address"] } } }
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.domain.erros import erros


def validar[T: BaseModel](esquema: type[T], dados: object) -> T:
    try:
        return esquema.model_validate(dados)
    except ValidationError as erro:
        detalhes: dict[str, list[str]] = {}
        for item in erro.errors():
            campo = ".".join(str(parte) for parte in item["loc"]) or "corpo"
            detalhes.setdefault(campo, []).append(item["msg"])
        raise erros.dados_invalidos(detalhes) from erro
