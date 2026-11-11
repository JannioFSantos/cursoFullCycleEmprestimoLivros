"""Criação do engine e da fábrica de sessões do SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def criar_engine(database_url: str) -> Engine:
    """Cria o engine.

    `pool_pre_ping=True` testa a conexão antes de usar. Isso evita o erro
    clássico de pegar uma conexão que o PostgreSQL já fechou por inatividade.
    """
    return create_engine(database_url, pool_pre_ping=True, future=True)


def criar_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Fábrica de sessões.

    `expire_on_commit=False` permite ler os atributos do objeto depois do
    commit, o que é útil quando o repositório monta a dataclass de retorno.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
