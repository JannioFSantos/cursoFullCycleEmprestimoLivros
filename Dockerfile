# Imagem de produção da API.
#
# Duas etapas: uma instala as dependências, a outra leva só o necessário para
# rodar. Isso mantém a imagem final pequena e sem compilador.

FROM python:3.12-slim AS dependencias

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Só o requirements entra antes do código: assim o cache do Docker não é
# invalidado a cada mudança em um arquivo .py.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# ------------------------------ imagem final ------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# curl é usado pelo HEALTHCHECK do Compose/Coolify.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Usuário sem privilégios: se alguém entrar no container, não é root.
RUN useradd --create-home --uid 10001 app

WORKDIR /app

COPY --from=dependencias /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencias /usr/local/bin /usr/local/bin

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY docs/openapi.yaml ./docs/openapi.yaml
COPY scripts ./scripts

RUN chmod +x scripts/entrypoint.sh && chown -R app:app /app

USER app

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:3000/health || exit 1

# Gunicorn sobe via scripts/entrypoint.sh, que antes aplica as migrações.
CMD ["./scripts/entrypoint.sh"]
