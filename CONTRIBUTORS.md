# Contribuidores

Projeto individual (Projeto B).

## Jannio Ferreira dos Santos

Fiz todas as partes do projeto:

- **M1:** Docker Compose, organização em camadas, padrão Repository e a
  transação com `FOR UPDATE` (SQLAlchemy).
- **M2:** testes unitários, teste de integração, cobertura e pipeline do
  GitHub Actions.
- **M3:** `.env.example`, logs em JSON, métricas e o SLO.
- **M4:** README, ADR, OpenAPI, testes de carga com Locust e o documento de
  desempenho.

O histórico de commits mostra a ordem em que fui construindo: base, domínio,
API, testes, carga e documentação.

Nesta versão, portei o projeto de TypeScript/Node/Fastify/Prisma para
Python/Flask/SQLAlchemy/Alembic. Mantive o mesmo contrato de API e a mesma
separação de camadas; troquei o k6 pelo Locust e a tela de demonstração por
páginas Jinja renderizadas no servidor, sem JavaScript.
