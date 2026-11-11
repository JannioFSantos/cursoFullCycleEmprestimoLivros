"""Configuração do ambiente de migrações.

O Alembic é o "controle de versão" do banco: cada arquivo em `versions/` é um
passo aplicado em ordem. Aqui só ligamos o Alembic à configuração da aplicação
e aos modelos do SQLAlchemy.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import carregar_configuracao
from app.infra.modelos import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# `target_metadata` é o que permite `alembic revision --autogenerate` comparar
# os modelos Python com o banco real.
target_metadata = Base.metadata


def _url_do_banco() -> str:
    """Prioriza a URL passada pelo chamador (testes); senão lê o ambiente."""
    return config.get_main_option("sqlalchemy.url") or carregar_configuracao().database_url


def run_migrations_offline() -> None:
    """Gera o SQL sem abrir conexão (`alembic upgrade head --sql`)."""
    context.configure(
        url=_url_do_banco(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica as migrações conectando no PostgreSQL."""
    secao = config.get_section(config.config_ini_section) or {}
    secao["sqlalchemy.url"] = _url_do_banco()

    connectable = engine_from_config(
        secao,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
