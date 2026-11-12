#!/bin/sh
# Sobe a aplicação em produção:
#   1. aplica as migrações do banco (idempotente: `upgrade head` não repete o
#      que já foi aplicado);
#   2. garante os dados de exemplo (também idempotente: só cria o que falta);
#   3. entrega o processo ao Gunicorn.
#
# `exec` é importante: o Gunicorn passa a ser o PID 1 e recebe o SIGTERM do
# Docker/Coolify diretamente, encerrando sem deixar requisição pela metade.
set -eu

echo "==> Aplicando migrações (alembic upgrade head)"
alembic upgrade head

# O seed cria os 10 livros e os 5 usuários de demonstração que ainda não
# existem. Para desligar (ex.: banco com dados reais), defina
# SEED_ON_START=false nas variáveis de ambiente.
if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "==> Garantindo dados de exemplo (python -m scripts.seed)"
  python -m scripts.seed
else
  echo "==> Seed desligado (SEED_ON_START=false)"
fi

echo "==> Iniciando Gunicorn na porta ${PORT:-3000}"
exec gunicorn \
  --bind "0.0.0.0:${PORT:-3000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "app:create_app()"
