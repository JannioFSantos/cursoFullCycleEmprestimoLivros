"""Schemas de entrada da API (validação com Pydantic).

Validar na borda é uma decisão de arquitetura: o domínio pode confiar que os
dados chegaram no formato certo. Nenhum caso de uso precisa checar "isso é
string?", "esse e-mail é válido?".

`extra="forbid"` recusa campos desconhecidos. Isso evita que um erro de
digitação do cliente (ex.: "email" em vez de "e-mail") passe silenciosamente.

Os campos internos são snake_case, mas a API aceita (e devolve) camelCase.
`alias_generator=to_camel` faz essa ponte automaticamente.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class ModeloDeEntrada(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class EsquemaNovoLivro(ModeloDeEntrada):
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=200)
    isbn: str = Field(min_length=10, max_length=20)
    # Pydantic converte "3" em 3, o que é amigável para quem testa com curl.
    exemplares_total: int = Field(ge=1, le=10_000)


class EsquemaNovoUsuario(ModeloDeEntrada):
    nome: str = Field(min_length=1, max_length=200)
    email: EmailStr = Field(max_length=200)


class EsquemaNovoEmprestimo(ModeloDeEntrada):
    livro_id: UUID
    usuario_id: UUID


class EsquemaParametroId(BaseModel):
    id: UUID


# ---------------------------------------------------------------------------
# Conversão para os dados que os repositórios entendem
# ---------------------------------------------------------------------------


def dados_novo_livro(esquema: EsquemaNovoLivro):
    from app.domain.repositorios import DadosNovoLivro

    return DadosNovoLivro(
        titulo=esquema.titulo,
        autor=esquema.autor,
        isbn=esquema.isbn,
        exemplares_total=esquema.exemplares_total,
    )


def dados_novo_usuario(esquema: EsquemaNovoUsuario):
    from app.domain.repositorios import DadosNovoUsuario

    return DadosNovoUsuario(nome=esquema.nome, email=str(esquema.email))
