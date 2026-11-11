"""Exclusão lógica de livros e usuários.

Revision ID: 0002_exclusao_logica
Revises: 0001_inicial
Create Date: 2026-11-10 01:17:58

`excluido_em` preenchido significa "saiu do catálogo/lista, mas tem histórico".
Quando não há empréstimo nenhum, o registro continua sendo apagado de verdade.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_exclusao_logica"
down_revision: str | None = "0001_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("livros", sa.Column("excluido_em", sa.DateTime(), nullable=True))
    op.add_column(
        "usuarios", sa.Column("excluido_em", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("usuarios", "excluido_em")
    op.drop_column("livros", "excluido_em")
