# ---------------------------------------------------------------------------
# Imagem de produção da API.
#
# Multi-stage:
#   1. build   -> instala TUDO (inclui devDependencies) e compila TypeScript
#   2. runtime -> instala só dependências de produção e copia o dist pronto
#
# Isso mantém a imagem final menor e sem as ferramentas de teste/lint.
# ---------------------------------------------------------------------------

# ---------- Estágio 1: build ----------
FROM node:22-alpine AS build

WORKDIR /app

# openssl é exigido pelos engines do Prisma.
RUN apk add --no-cache openssl

# Copiamos primeiro só os manifests para aproveitar o cache de camadas:
# se o código mudar mas as dependências não, o npm ci não roda de novo.
COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json tsconfig.build.json ./
COPY prisma ./prisma
RUN npx prisma generate

COPY src ./src
RUN npm run build

# ---------- Estágio 2: runtime ----------
FROM node:22-alpine AS runtime

WORKDIR /app

RUN apk add --no-cache openssl

ENV NODE_ENV=production

# Só dependências de produção. O Prisma CLI está em "dependencies" porque é
# ele que roda `prisma migrate deploy` na inicialização do container.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY prisma ./prisma
RUN npx prisma generate

COPY --from=build /app/dist ./dist
# O Swagger UI lê este arquivo em tempo de execução (rota /API/docs).
COPY docs ./docs
# A tela de demonstração (/) também é lida em tempo de execução.
COPY public ./public
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x ./scripts/entrypoint.sh

# Rodar como usuário sem privilégios é uma boa prática de segurança.
USER node

ENV PORT=3000
ENV HOST=0.0.0.0

EXPOSE 3000

# O Coolify também pode usar este HEALTHCHECK. Se /health devolver 503
# (banco fora), o container é considerado unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

ENTRYPOINT ["./scripts/entrypoint.sh"]
