# Roteiro da apresentação (10 minutos)

Minha ideia é seguir o que o professor pediu: 1 minuto do problema, 3 minutos
de demonstração, 3 minutos de uma decisão e 3 minutos de números.

## Antes de começar

Deixar aberto:

- o terminal na pasta do projeto;
- o navegador em `http://localhost:3000`;
- o arquivo `docs/desempenho.md`;
- o GitHub Actions com o CI verde.

Subir a API:

```bash
docker compose up -d --build
curl http://localhost:3000/health
```

## Minuto 0 a 1 — O problema

Falar mais ou menos assim:

> "Meu projeto é uma API de empréstimo de livros. Ela cadastra livro e usuário,
> empresta, devolve e lista atrasados. O problema de verdade não é o CRUD: é
> impedir que duas pessoas levem o mesmo último exemplar ao mesmo tempo.
>
> Escolhi o Projeto B porque tinha pouco tempo e preferi entregar um fluxo
> pequeno funcionando do que um projeto grande pela metade."

Mostrar a primeira linha do README: `Nível: Projeto B`.

## Minuto 1 a 4 — Demonstração

Cadastrar livro, usuário e emprestar:

```bash
curl -s -X POST http://localhost:3000/livros \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"DDD","autor":"Eric Evans","isbn":"9780321125217","exemplaresTotal":1}'

curl -s -X POST http://localhost:3000/usuarios \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Ana","email":"ana@exemplo.com"}'

curl -s -X POST http://localhost:3000/emprestimos \
  -H 'Content-Type: application/json' \
  -d '{"livroId":"<ID>","usuarioId":"<ID>"}'
```

Depois, com um segundo usuário, tentar o mesmo livro:

```bash
curl -s -X POST http://localhost:3000/emprestimos \
  -H 'Content-Type: application/json' \
  -d '{"livroId":"<ID>","usuarioId":"<OUTRO_ID>"}'
```

Mostrar o `409 LIVRO_INDISPONIVEL` e falar:

> "Esse 409 não é erro do sistema. É a regra funcionando. O teste de integração
> prova esse caminho."

Ainda na demo:

```bash
curl -s -X PATCH http://localhost:3000/emprestimos/<ID>/devolucao
curl -s http://localhost:3000/metrics | grep emprestimos_total
```

## Minuto 4 a 7 — A decisão

Abrir `docs/adr/0001-disponibilidade.md` e explicar com as minhas palavras:

> "O jeito simples é contar, verificar e inserir. Com duas requisições juntas,
> as duas contam antes de qualquer inserção e as duas passam.
>
> Eu poderia guardar uma coluna com os exemplares disponíveis. Descartei
> porque vira uma segunda fonte de verdade e pode ficar errada.
>
> Também poderia usar Redis. Descartei porque era infraestrutura demais para o
> problema.
>
> A decisão foi travar a linha do livro com `SELECT ... FOR UPDATE` dentro de
> uma transação. Quem chega depois espera."

Se perguntarem do custo:

> "O custo é que pedidos do mesmo livro ficam em fila. Isso apareceu no teste
> de carga: a escrita ficou com p95 de 264 ms contra 41 ms da leitura."

## Minuto 7 a 10 — Números

Mostrar a tabela de `docs/desempenho.md`:

- smoke: 5/5 checks, p95 de 58,83 ms;
- carga: ~687 req/s;
- leitura p95 de 41,28 ms;
- escrita p95 de 264,48 ms;
- índice: 0,601 ms com e 2,439 ms sem.

Fechar:

> "O que eu faria diferente com mais tempo: cache no `GET /livros`, um teste
> com livros diferentes e talvez um painel no Grafana. O que eu não faria é
> aumentar o escopo. O Projeto B só vale se o fluxo inteiro funcionar."

## Perguntas que podem aparecer

| Pergunta | Resposta curta |
| --- | --- |
| Por que não usar `SERIALIZABLE`? | Ia aumentar o custo e os retries; o `FOR UPDATE` resolve o ponto exato da disputa. |
| E se o processo morrer no meio? | A transação que não terminou é desfeita pelo PostgreSQL. |
| Por que UUID? | Não mostra o volume de registros e dá para gerar antes de inserir. |
| Como o Coolify sabe se está ok? | O healthcheck chama `/health`, que também testa o banco. |
| Onde ficam as senhas? | Só no painel do Coolify. No repositório tem apenas `.env.example`. |
| 90% de cobertura é real? | Sim, medido em `src/domain` e `src/use-cases`, que é onde ficam as regras. |
