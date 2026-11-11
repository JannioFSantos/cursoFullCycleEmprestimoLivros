# Desempenho

Aqui estão os números que medi e como medi. Não coloquei estimativa: tudo saiu
de execução de verdade.

## Onde rodei

- Windows 11 com Docker Desktop;
- API em container `python:3.12-slim`, com Gunicorn (2 workers e 4 threads);
- PostgreSQL em container `postgres:16-alpine`;
- Locust rodando na máquina host, apontando para `http://127.0.0.1:3000/API`;
- sem cache e sem tuning.

Usei `127.0.0.1` em vez de `localhost` de propósito: no Windows, o
`localhost` pode tentar IPv6 primeiro e adicionar cerca de 2 segundos por
requisição, o que estragaria a medição.

## Smoke test

O `locust/smoke.py` faz o fluxo completo uma vez: cria livro, cria usuário,
empresta, devolve e lista atrasados.

```bash
locust -f locust/smoke.py --headless -u 1 -r 1 -t 10s --only-summary
```

| Item | Resultado |
| --- | --- |
| Requisições | 5 |
| Falhas | 0 |
| Tempo máximo | 48 ms |

Se esse teste falhar, não adianta rodar o teste de carga.

## Teste de carga

O `locust/load.py` roda 1 minuto com dois cenários ao mesmo tempo:

- leitores, com peso 2, chamando `GET /livros`;
- escritores, com peso 1, criando empréstimos em `POST /emprestimos`.

```bash
locust -f locust/load.py --headless -u 30 -r 5 -t 1m --only-summary
```

Um detalhe importante: no teste de escrita, **todos pedem o mesmo livro**. O
cenário cria um livro com 5.000 exemplares e 300 usuários, e cada escritor
sorteia um usuário. Fiz assim de propósito para forçar a disputa pelo
`FOR UPDATE`. Na vida real os pedidos se espalham entre vários livros.

| Item | Resultado |
| --- | --- |
| Usuários virtuais | 30 |
| Duração | 60 s |
| Total de requisições | 4.539 |
| Requisições por segundo | 77,29 |
| Falhas técnicas | 0 |

| Cenário | p95 | Limite | Passou? |
| --- | --- | --- | --- |
| Leitura (`GET /livros`) | 85 ms | 300 ms | Sim |
| Escrita (`POST /emprestimos`) | 150 ms | 500 ms | Sim |
| Agregado | 120 ms | — | — |

O próprio `locust/load.py` verifica o SLO no fim do teste. Se o p95 de leitura
passar de 300 ms ou o de escrita passar de 500 ms, o processo termina com
código de saída `1` — assim o teste de carga também serve de portão no CI ou
numa execução manual.

### Por que aparecem respostas 409

No cenário de escrita, o `409` é esperado: cada usuário só pode ter 3
empréstimos ativos e o limite é uma regra de negócio, não uma falha técnica.
Por isso o teste considera `201` **e** `409` como sucesso. O que ele mede de
verdade é o tempo e a ausência de erros `5xx`.

Olhar só a taxa de erro bruta do Locust engana neste projeto. O que importa é
o check de negócio (201 ou 409) e o p95.

### Por que a escrita é mais lenta

A leitura faz uma consulta simples. A escrita faz, dentro de uma transação:

1. trava a linha do livro;
2. trava a linha do usuário;
3. faz três consultas de contagem;
4. insere o empréstimo.

Com todo mundo pedindo o mesmo livro, as transações esperam umas pelas outras.
Por isso o p95 fica em 150 ms, contra 85 ms da leitura. É o custo de garantir
que o mesmo exemplar não seja emprestado duas vezes.

## Teste do índice

Para ver se o índice faz diferença, gerei 20 mil empréstimos com
`python -m scripts.seed_volume` e rodei a consulta da disponibilidade com e sem
o índice `(livro_id, status)`.

```sql
SELECT count(*) FROM emprestimos
WHERE livro_id = $1 AND status = 'ATIVO';
```

| Situação | Plano | Buffers | Tempo |
| --- | --- | --- | --- |
| Com índice | `Index Only Scan` | 196 | 1,180 ms |
| Sem índice | `Seq Scan` (19.751 linhas filtradas) | 287 | 3,406 ms |

Com o índice foi quase 3 vezes mais rápido e leu menos páginas do banco. O
índice já está na migration `0001_inicial` e é recriado por
`alembic upgrade head`.

O script `scripts/seed_volume.py` apaga os empréstimos existentes antes de
inserir os 20 mil. Use só no banco local.

## O que eu faria diferente

1. Fazer um teste de carga com livros diferentes, para comparar com esse pior
   caso.
2. Colocar cache no `GET /livros`, que é a maior parte das requisições.
3. Se um dia precisar, travar por usuário para melhorar a disputa do limite de
   3 empréstimos.

O que eu não faria é trocar o `FOR UPDATE` por uma coluna contador só para
melhorar o número. O risco de dado errado não compensa.

## Como reproduzir

Suba o banco e a API:

```bash
docker compose up -d --build
```

Rode os testes de carga na máquina host (com as dependências de
desenvolvimento instaladas):

```bash
locust -f locust/smoke.py --headless -u 1 -r 1 -t 10s --only-summary
locust -f locust/load.py --headless -u 30 -r 5 -t 1m --only-summary
```

Para medir o índice, use o banco local:

```bash
# com o .env apontando para localhost:5432/biblioteca
alembic upgrade head
python -m scripts.seed_volume

docker exec -it biblioteca-db psql -U postgres -d biblioteca
```

Dentro do `psql`:

```sql
-- pegue um id de livro do volume
SELECT id FROM livros WHERE isbn LIKE 'volume-%' LIMIT 1;

-- com índice
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM emprestimos
WHERE livro_id = '<id>' AND status = 'ATIVO';

-- sem índice
DROP INDEX emprestimos_livro_id_status_idx;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM emprestimos
WHERE livro_id = '<id>' AND status = 'ATIVO';

-- recrie no fim
CREATE INDEX emprestimos_livro_id_status_idx
  ON emprestimos (livro_id, status);
```

Para apontar o Locust para outro ambiente, use `BASE_URL`:

```bash
BASE_URL=https://agendadeconsultas.v6.rocks/API \
  locust -f locust/smoke.py --headless -u 1 -r 1 -t 10s
```
