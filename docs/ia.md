# Uso de IA neste projeto

O curso permite e espera uso de IA. A regra que segui: **a decisão continua
sendo minha; código que eu não sei explicar não conta como meu.** Este arquivo
registra os prompts que realmente mudaram o projeto e o que foi aceito ou
recusado.

## Prompts que importaram

### 1. Desenho inicial do Projeto B

> "Tenho 8 dias para entregar o Projeto B do Full Cycle: uma API de domínio
> único com Compose, SOLID, 1 pattern, testes unitários + 1 integração,
> coverage, CI, logs, 1 métrica, 1 SLO, README, 1 ADR, OpenAPI e 1 smoke test
> k6. Proponha um domínio com um fluxo principal e regras testáveis sem
> infraestrutura extra."

**Aceitei:** domínio de biblioteca com empréstimo/devolução e a ideia de usar
`SELECT ... FOR UPDATE` como decisão arquitetural documentável.

**Recusei:** a sugestão de incluir fila/idempotência. Isso é escopo do Projeto
A e colocaria o prazo em risco.

### 2. Revisão da concorrência

> "Explique por que uma coluna `exemplares_disponiveis` desnormalizada é pior
> que contar empréstimos ativos dentro de uma transação com `FOR UPDATE`.
> Quero alternativas descartadas para o ADR."

**Aceitei:** a estrutura de alternativas (contador, Redis, constraint única
parcial) e a ordem de locks para evitar deadlock.

**Recusei:** sugerir Redis. Não se justifica no volume do projeto.

### 3. Testes

> "Liste os casos de teste que provam as três regras de empréstimo, incluindo
> os caminhos de erro, e um teste de integração que use `app.inject` do Fastify
> contra PostgreSQL real."

**Aceitei:** a lista de casos e a ideia de injetar um relógio controlável para
simular atraso sem esperar 14 dias.

**Ajustei:** o teste de ISBN duplicado foi reescrito para usar um ISBN fixo em
vez de inferir o valor, que ficava frágil.

### 4. Deploy no Coolify

> "Quais são os passos e os erros comuns ao publicar uma API Node + Prisma +
> PostgreSQL no Coolify usando Dockerfile? Como rodar migrations no boot?"

**Aceitei:** `prisma migrate deploy` no entrypoint, `HOST=0.0.0.0`, healthcheck
em `/health` e uso da URL interna do PostgreSQL.

**Verifiquei por conta própria:** o Dockerfile multi-stage e o usuário `node`
sem privilégios.

## O que eu conferi sem IA

- Todas as migrations foram geradas pelo Prisma e revisadas antes do commit.
- Os números de `docs/desempenho.md` vieram da execução local do k6, não de
  estimativa.
- Todo comando do README foi executado em uma máquina limpa antes da entrega.
- A explicação do ADR foi escrita com minhas palavras e é o que eu defendo na
  apresentação.
