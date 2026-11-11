"""Entidades do domínio.

São dataclasses "puras": não sabem que existe SQLAlchemy, Flask ou PostgreSQL.
Isso é o que permite testar as regras de negócio sem subir banco nenhum.

Os nomes dos atributos ficam em snake_case (convenção do Python). A conversão
para o camelCase da API acontece só na borda HTTP, em `app/http/serializacao.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class StatusEmprestimo(StrEnum):
    """Um empréstimo só pode estar em um destes dois estados."""

    ATIVO = "ATIVO"
    DEVOLVIDO = "DEVOLVIDO"


@dataclass
class Livro:
    id: UUID
    titulo: str
    autor: str
    isbn: str
    """Quantos exemplares físicos a biblioteca possui."""
    exemplares_total: int
    criado_em: datetime
    """
    None = livro no catálogo.
    Preenchido = livro que saiu do catálogo, mas tem histórico de empréstimo.
    Nesse caso a linha continua no banco para o histórico não ser perdido.
    """
    excluido_em: datetime | None = None


@dataclass
class Usuario:
    id: UUID
    nome: str
    email: str
    criado_em: datetime
    """Mesma ideia do livro: preenchido quando saiu da lista, mas tem histórico."""
    excluido_em: datetime | None = None


@dataclass
class Emprestimo:
    id: UUID
    livro_id: UUID
    usuario_id: UUID
    status: StatusEmprestimo
    data_emprestimo: datetime
    """Data limite para devolver (sempre à meia-noite UTC)."""
    data_prevista: datetime
    """None enquanto o livro não foi devolvido."""
    data_devolucao: datetime | None = None


@dataclass
class LivroResumo:
    """Dados mínimos do livro usados dentro do histórico de empréstimos."""

    id: UUID
    titulo: str
    autor: str
    excluido_em: datetime | None = None


@dataclass
class UsuarioResumo:
    """Dados mínimos do usuário usados dentro do histórico de empréstimos."""

    id: UUID
    nome: str
    email: str
    excluido_em: datetime | None = None


@dataclass
class EmprestimoDetalhado(Emprestimo):
    """Empréstimo com os dados do livro e do usuário já incluídos."""

    livro: LivroResumo = None  # type: ignore[assignment]
    usuario: UsuarioResumo = None  # type: ignore[assignment]


@dataclass
class LivroComDisponibilidade(Livro):
    """Livro + números calculados na hora da consulta.

    `exemplares_disponiveis` NÃO é uma coluna do banco: é sempre recalculado
    para não ficar desatualizado (ver ADR 0001).
    """

    emprestimos_ativos: int = 0
    exemplares_disponiveis: int = 0
