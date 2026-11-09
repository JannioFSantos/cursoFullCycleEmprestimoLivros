# Desempenho

Aqui estão os números que medi e como medi. Não coloquei estimativa: tudo saiu
de execução de verdade.

## Onde rodei

- Windows 11 com Docker Desktop;
- API em container `node:22-alpine`;
- PostgreSQL em container `postgres:16-alpine`;
- k6 em container, na mesma rede;
- sem cache e sem tuning.

## Smoke test

O `k6/smoke.js` faz o fluxo completo uma vez: cria livro, cria usuário,
empresta, devolve e lista atrasados.

| Item | Resultado |
| --- | --- |
| Checks | 5 de 5 (100%) |
| Requisições com erro | 0% |
| p95 | 58,83 ms |

## Teste de carga

O `k6/load.js` roda 1 minuto com dois cenários ao mesmo tempo:

- 20 usuários virtuais lendo `GET /livros`;
- até 10 usuários virtuais criando empréstimos em `POST /emprestimos`.

Um detalhe importante: no teste de escrita, **todos pedem o mesmo livro**.
Fiz assim de propósito para forçar a disputa pelo `FOR UPDATE`. Na vida real
os pedidos se espalham entre vários livros.

| Item | Resultado |
| --- | --- |
| Total de requisições | 42.947 |
| Requisições por segundo | ~687 |
| Checks | 100% (42.646 de 42.646) |

| Cenário | p90 | p95 | Limite | Passou? |
| --- | --- | --- | --- | --- |
| Leitura (`GET /livros`) | 37,44 ms | 41,28 ms | 300 ms | Sim |
| Escrita (`POST /emprestimos`) | 242,37 ms | 264,48 ms | 500 ms | Sim |

### Por que apareceram 409

No cenário de escrita, 1.513 de 2.710 requisições receberam `409`. Isso está
certo: cada usuário só pode ter 3 empréstimos ativos, e o teste tinha 300
usuários. O k6 conta `409` como requisição "falha" por padrão, por isso o
número geral de erro apareceu como 3,52%, mesmo com 100% dos checks passando.

Ou seja: nesse projeto, olhar só a taxa de erro do k6 engana. O que importa é
o check de negócio (201 ou 409) e o tempo.

### Por que a escrita é mais lenta

A leitura faz uma consulta simples. A escrita faz, dentro de uma transação:

1. trava a linha do livro;
2. trava a linha do usuário;
3. faz três consultas de contagem;
4. insere o empréstimo.

Com todo mundo pedindo o mesmo livro, as transações esperam umas pelas outras.
Por isso o p95 fica em 264 ms. É o custo de garantir que o mesmo exemplar não
seja emprestado duas vezes.

## Teste do índice

Para ver se o índice faz diferença, gerei 20 mil empréstimos com
`npm run db:seed:volume` e rodei a consulta da disponibilidade com e sem o
índice `(livro_id, status)`.

```sql
SELECT count(*) FROM emprestimos
WHERE livro_id = $1 AND status = 'ATIVO';
```

| Situação | Plano | Buffers | Tempo |
| --- | --- | --- | --- |
| Com índice | Index Only Scan | 42 | 0,601 ms |
| Sem índice | Seq Scan (19.960 linhas filtradas) | 266 | 2,439 ms |

Com o índice foi umas 4 vezes mais rápido e leu bem menos páginas do banco. O
índice já está no `schema.prisma` e vai junto na migration.

A consulta de atrasados usa o índice `(status, data_prevista)` e levou 7,3 ms
para 14.990 linhas.

## O que eu faria diferente

1. Fazer um teste de carga com livros diferentes, para comparar com esse pior
   caso.
2. Colocar cache no `GET /livros`, que é a maior parte das requisições.
3. Se um dia precisar, travar por usuário para melhorar a disputa do limite de
   3 empréstimos.

O que eu não faria é trocar o `FOR UPDATE` por uma coluna contador só para
melhorar o número. O risco de dado errado não compensa.

## Como reproduzir

```bash
docker compose up -d --build

docker run --rm --network cursofullcycleemprestimolivros_default \
  -e BASE_URL=http://api:3000 -v "${PWD}/k6:/scripts" \
  grafana/k6 run /scripts/smoke.js

docker run --rm --network cursofullcycleemprestimolivros_default \
  -e BASE_URL=http://api:3000 -v "${PWD}/k6:/scripts" \
  grafana/k6 run /scripts/load.js
```

O `npm run db:seed:volume` apaga os empréstimos existentes. Use só no banco
local.
