#!/bin/sh
# Sobe a aplicação em produção:
#   1. aplica as migrações do banco (idempotente: `upgrade head` não repete o
#      que já foi aplicado);
#   2. entrega o processo ao Gunicorn.
#
# `exec` é importante: o Gunicorn passa a ser o PID 1 e recebe o SIGTERM do
# Docker/Coolify diretamente, encerrando sem deixar requisição pela metade.
set -eu

echo "==> Aplicando migrações (alembic upgrade head)"
alembic upgrade head

echo "==> Iniciando Gunicorn na porta ${PORT:-3000}"
exec gunicorn \
  --bind "0.0.0.0:${PORT:-3000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "app:create_app()"
