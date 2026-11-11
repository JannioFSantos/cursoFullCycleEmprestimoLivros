"""Estrutura inicial: livros, usuários e empréstimos.

Revision ID: 0001_inicial
Revises:
Create Date: 2025-11-05 00:00:00

Este arquivo reproduz exatamente o schema que o Prisma criava na versão
TypeScript do projeto. A intenção é que o banco continue o mesmo, então quem já
tinha dados não precisa migrar nada.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS public")

    status_emprestimo = postgresql.ENUM(
        "ATIVO", "DEVOLVIDO", name="status_emprestimo", create_type=False
    )
    status_emprestimo.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "livros",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("autor", sa.Text(), nullable=False),
        sa.Column("isbn", sa.Text(), nullable=False),
        sa.Column("exemplares_total", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="livros_pkey"),
    )
    op.create_index("livros_isbn_key", "livros", ["isbn"], unique=True)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="usuarios_pkey"),
    )
    op.create_index("usuarios_email_key", "usuarios", ["email"], unique=True)

    op.create_table(
        "emprestimos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("livro_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            status_emprestimo,
            server_default="ATIVO",
            nullable=False,
        ),
        sa.Column("data_emprestimo", sa.DateTime(), nullable=False),
        sa.Column("data_prevista", sa.DateTime(), nullable=False),
        sa.Column("data_devolucao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["livro_id"],
            ["livros.id"],
            name="emprestimos_livro_id_fkey",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name="emprestimos_usuario_id_fkey",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="emprestimos_pkey"),
    )
    op.create_index(
        "emprestimos_livro_id_status_idx",
        "emprestimos",
        ["livro_id", "status"],
    )
    op.create_index(
        "emprestimos_usuario_id_status_idx",
        "emprestimos",
        ["usuario_id", "status"],
    )
    op.create_index(
        "emprestimos_status_data_prevista_idx",
        "emprestimos",
        ["status", "data_prevista"],
    )


def downgrade() -> None:
    op.drop_index("emprestimos_status_data_prevista_idx", table_name="emprestimos")
    op.drop_index("emprestimos_usuario_id_status_idx", table_name="emprestimos")
    op.drop_index("emprestimos_livro_id_status_idx", table_name="emprestimos")
    op.drop_table("emprestimos")
    op.drop_index("usuarios_email_key", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_index("livros_isbn_key", table_name="livros")
    op.drop_table("livros")
    op.execute("DROP TYPE IF EXISTS status_emprestimo")
