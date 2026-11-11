"""Fixtures dos testes de integração.

Os testes de integração usam PostgreSQL de verdade. A fixture cria as tabelas a
partir dos modelos SQLAlchemy e limpa tudo entre os testes.

Preparo local:

    docker compose up -d db
    set TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/biblioteca_test
    pytest tests/integration

Sem banco disponível, os testes de integração são marcados como "skip" com uma
mensagem explicando o que fazer — em vez de falhar com um erro confuso.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import Configuracao
from app.fabrica import criar_app
from app.infra.modelos import Base


class RelogioControlado:
    """Relógio que o teste move para simular a passagem dos dias."""

    def __init__(self, agora: datetime) -> None:
        self.instante = agora

    def agora(self) -> datetime:
        return self.instante


def _url_do_banco() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/biblioteca_test",
    )


@pytest.fixture(scope="session")
def engine():
    motor = create_engine(_url_do_banco(), pool_pre_ping=True)

    try:
        with motor.connect() as conexao:
            conexao.execute(text("SELECT 1"))
    except OperationalError as erro:  # pragma: no cover - depende do ambiente
        pytest.skip(
            "Banco indisponível. Suba com 'docker compose up -d db' e rode as "
            f"migrações. Detalhe: {erro}"
        )

    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)

    yield motor

    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture()
def sessao(engine):
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    yield fabrica


@pytest.fixture()
def relogio():
    return RelogioControlado(datetime(2026, 1, 5, 12))


@pytest.fixture()
def app(engine, relogio):
    configuracao = Configuracao(
        ambiente="test",
        database_url=_url_do_banco(),
        prazo_dias=14,
        limite_emprestimos=3,
    )
    aplicacao = criar_app(configuracao, engine=engine, relogio=relogio)
    aplicacao.config.update(TESTING=False)
    return aplicacao


@pytest.fixture()
def cliente(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def limpar_banco(engine):
    """Zera as tabelas antes de cada teste (ordem por causa das FKs)."""
    yield
    with engine.begin() as conexao:
        conexao.execute(text("DELETE FROM emprestimos"))
        conexao.execute(text("DELETE FROM livros"))
        conexao.execute(text("DELETE FROM usuarios"))


@pytest.fixture()
def avancar_dias(relogio):
    def avancar(dias: int) -> None:
        relogio.instante = relogio.instante + timedelta(days=dias)

    return avancar
