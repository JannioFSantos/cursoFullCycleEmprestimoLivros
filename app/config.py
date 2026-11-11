"""Configuração da aplicação.

Um único lugar lê variáveis de ambiente e valida os valores. O resto do
código recebe um objeto `Configuracao` já pronto, do mesmo jeito que o
projeto TypeScript recebia `env`.

Se faltar alguma variável obrigatória, a aplicação falha na inicialização com
uma mensagem clara, em vez de estourar um erro confuso na primeira requisição.
"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Carrega o .env antes de ler o ambiente. Em produção (Coolify) o arquivo não
# existe: o python-dotenv simplesmente não encontra nada e segue em frente.
load_dotenv()

Ambiente = Literal["development", "test", "production"]


class Configuracao(BaseModel):
    """Variáveis de ambiente já validadas e tipadas."""

    model_config = ConfigDict(extra="ignore")

    ambiente: Ambiente = "development"
    porta: int = Field(default=3000, gt=0, le=65535)
    host: str = Field(default="0.0.0.0", min_length=1)
    log_level: str = "info"
    database_url: str = Field(min_length=1)
    # Usada para assinar o cookie de sessão (mensagens flash da tela demo).
    # Em produção, defina SECRET_KEY no Coolify; o padrão serve só para dev.
    secret_key: str = Field(default="chave-de-desenvolvimento", min_length=1)
    prazo_dias: int = Field(default=14, gt=0)
    limite_emprestimos: int = Field(default=3, gt=0)

    @field_validator("log_level")
    @classmethod
    def validar_log_level(cls, valor: str) -> str:
        permitidos = {"fatal", "error", "warning", "warn", "info", "debug", "trace"}
        normalizado = valor.lower()
        if normalizado not in permitidos:
            raise ValueError(
                f"LOG_LEVEL inválido: {valor!r}. Use um de: {', '.join(sorted(permitidos))}."
            )
        return normalizado

    @field_validator("database_url")
    @classmethod
    def normalizar_url_do_banco(cls, valor: str) -> str:
        """Aceita a URL no formato antigo e aponta para o driver psycopg 3.

        O projeto anterior usava `postgresql://...` (driver padrão do Prisma).
        No SQLAlchemy precisamos dizer qual driver usar. Fazemos a troca aqui
        para que a URL do Coolify continue funcionando sem mudança manual.
        """
        if valor.startswith("postgresql://"):
            return valor.replace("postgresql://", "postgresql+psycopg://", 1)
        if valor.startswith("postgres://"):
            return valor.replace("postgres://", "postgresql+psycopg://", 1)
        return valor


def carregar_configuracao() -> Configuracao:
    """Lê e valida o ambiente. Levanta SystemExit com uma mensagem amigável."""
    dados = {
        # APP_ENV é o nome novo. NODE_ENV continua aceito para quem já tinha o
        # ambiente configurado no Coolify.
        "ambiente": os.getenv("APP_ENV") or os.getenv("NODE_ENV") or "development",
        "porta": os.getenv("PORT", "3000"),
        "host": os.getenv("HOST", "0.0.0.0"),
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "database_url": os.getenv("DATABASE_URL", ""),
        "secret_key": os.getenv("SECRET_KEY", "chave-de-desenvolvimento"),
        "prazo_dias": os.getenv("PRAZO_DIAS", "14"),
        "limite_emprestimos": os.getenv("LIMITE_EMPRESTIMOS", "3"),
    }

    try:
        return Configuracao.model_validate(dados)
    except Exception as erro:  # noqa: BLE001 - queremos mostrar tudo de uma vez
        print("❌ Variáveis de ambiente inválidas:")
        print(erro)
        print("💡 Copie o .env.example para .env e tente novamente.")
        raise SystemExit(1) from erro
