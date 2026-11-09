# Contribuidores

Projeto individual (Projeto B).

## Jannio Ferreira dos Santos

- **M1 — Funciona, código e design**
  - Docker Compose com API + PostgreSQL em um comando
  - domínio separado de infraestrutura e HTTP
  - padrão Repository com interfaces no domínio
  - transação com `SELECT ... FOR UPDATE` para a regra de disponibilidade

- **M2 — Testes e CI**
  - testes unitários das regras e dos casos de uso
  - teste de integração com API + banco reais
  - coverage mínimo de 90% em `src/domain` e `src/use-cases`
  - pipeline com lint, testes, cobertura, build e build da imagem Docker

- **M3 — Ambientes, segredos e observabilidade**
  - `.env.example` versionado e `.env` fora do repositório
  - logs estruturados com `requestId`
  - métrica `http_request_duration_seconds` e `emprestimos_total`
  - SLO de p95 declarado e medido

- **M4 — Arquitetura, documentação e desempenho**
  - ADR 0001 com alternativa descartada
  - OpenAPI 3.1 validado por Spectral no CI
  - smoke test e teste de carga com k6
  - `docs/desempenho.md` com metodologia, números e gargalo

## Como o trabalho foi organizado

O histórico de commits segue a ordem de construção: base e Compose, domínio,
API, testes, CI e documentação. Cada commit tem uma mensagem que explica a
mudança, e o README aponta para os artefatos de cada módulo.
