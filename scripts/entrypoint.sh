#!/bin/sh
# Entrypoint do container de produção.
#
# Responsabilidades:
#   1. aplicar as migrations pendentes do Prisma;
#   2. iniciar a API.
#
# Por que rodar migration no start? Em um deploy no Coolify não temos um passo
# separado garantido. O `migrate deploy` é idempotente: se não há nada novo,
# ele apenas não faz nada. É seguro rodar a cada boot.
#
# Se a migration falhar, o container morre (set -e) em vez de subir uma API
# incompatível com o banco. Isso é proposital.

set -e

echo "[entrypoint] aplicando migrations..."
./node_modules/.bin/prisma migrate deploy

echo "[entrypoint] iniciando API..."
exec node dist/server.js
