"""Modelos SQLAlchemy — o espelho das tabelas do PostgreSQL.

Decisões visíveis aqui:
 - nomes de tabela/coluna em snake_case, seguindo convenção SQL;
 - ids UUID em vez de inteiro sequencial (não expõem volume e são seguros);
 - índices compostos que sustentam as consultas do dia a dia;
 - `exemplares_disponiveis` NÃO existe de propósito (ver ADR 0001).

As entidades do domínio são dataclasses separadas (`app/domain/entidades.py`).
A conversão entre modelo e entidade acontece nos repositórios.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.entidades import StatusEmprestimo


def agora_utc() -> datetime:
    """Agora em UTC, sem tzinfo (o banco usa TIMESTAMP sem fuso)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class LivroModelo(Base):
    __tablename__ = "livros"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[str] = mapped_column(Text, nullable=False)
    isbn: Mapped[str] = mapped_column(Text, nullable=False)
    exemplares_total: Mapped[int] = mapped_column(nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=agora_utc, server_default=func.now()
    )
    # Preenchido quando o livro sai do catálogo, mas tem empréstimos antigos.
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    emprestimos: Mapped[list[EmprestimoModelo]] = relationship(
        back_populates="livro",
        lazy="raise",
    )

    __table_args__ = (
        Index("livros_isbn_key", "isbn", unique=True),
    )


class UsuarioModelo(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=agora_utc, server_default=func.now()
    )
    # Preenchido quando o usuário sai da lista, mas tem empréstimos antigos.
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    emprestimos: Mapped[list[EmprestimoModelo]] = relationship(
        back_populates="usuario",
        lazy="raise",
    )

    __table_args__ = (
        Index("usuarios_email_key", "email", unique=True),
    )


class EmprestimoModelo(Base):
    __tablename__ = "emprestimos"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    livro_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("livros.id", ondelete="RESTRICT"), nullable=False
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[StatusEmprestimo] = mapped_column(
        Enum(
            StatusEmprestimo,
            name="status_emprestimo",
            values_callable=lambda classe: [item.value for item in classe],
        ),
        nullable=False,
        default=StatusEmprestimo.ATIVO,
        server_default=StatusEmprestimo.ATIVO.value,
    )
    data_emprestimo: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Data limite de devolução, normalizada para 00:00 UTC.
    data_prevista: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_devolucao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    livro: Mapped[LivroModelo] = relationship(back_populates="emprestimos")
    usuario: Mapped[UsuarioModelo] = relationship(back_populates="emprestimos")

    __table_args__ = (
        # Índices que cobrem as consultas:
        #  - contar empréstimos ativos de um livro (disponibilidade)
        #  - contar empréstimos ativos de um usuário (limite de 3)
        #  - listar atrasados (status + data_prevista)
        Index("emprestimos_livro_id_status_idx", "livro_id", "status"),
        Index("emprestimos_usuario_id_status_idx", "usuario_id", "status"),
        Index("emprestimos_status_data_prevista_idx", "status", "data_prevista"),
    )
