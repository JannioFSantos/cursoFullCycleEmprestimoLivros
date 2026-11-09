# Desempenho — metodologia, números e gargalo

> **Regra deste documento:** todo número aqui foi medido, não estimado. Os
> comandos de reprodução estão no fim.

## Ambiente do teste

| Item | Valor |
| --- | --- |
| Data | 09/11/2026 |
| Máquina | Windows 11, Docker Desktop (WSL2) |
| API | container `node:22-alpine`, 1 processo Node |
| Banco | container `postgres:16-alpine` |
| Rede | containers na mesma rede local do Compose |
| Dados no banco no início | ~2.700 empréstimos (criados pelo próprio k6) |
| k6 | `grafana/k6` em container, na mesma rede |

Não houve tuning: sem pool extra, sem cache, sem réplica, sem índice novo. É o
projeto como está no repositório.

---

## 1. Smoke test (`k6/smoke.js`)

Um usuário virtual, uma iteração, fluxo completo: criar livro, criar usuário,
emprestar, devolver, listar atrasados.

| Métrica | Resultado | Threshold | Situação |
| --- | --- | --- | --- |
| Checks | 100% (5/5) | > 99% | ✅ |
| `http_req_failed` | 0,00% | < 1% | ✅ |
| p95 de duração | **58,83 ms** | < 300 ms | ✅ |

O smoke test é binário: se ele falha, o teste de carga não faz sentido.

---

## 2. Teste de carga (`k6/load.js`)

Dois cenários simultâneos por 1 minuto:

- **leituras:** 20 VUs em `GET /livros`;
- **escritas:** rampa de 0→10 VUs em `POST /emprestimos`.

Todas as escritas apontam para o **mesmo livro** de propósito. É o pior caso
para o `SELECT ... FOR UPDATE`: todo mundo disputa a mesma linha.

### Resultado geral

| Métrica | Valor |
| --- | --- |
| Requisições HTTP | 42.947 |
| Throughput | **~687 req/s** |
| Checks | **100%** (42.646/42.646) |
| Duração do teste | 1m02s |

### Por cenário

| Cenário | Requisições | p90 | **p95** | Threshold | Situação |
| --- | --- | --- | --- | --- | --- | --- |
| Leituras (`GET /livros`) | 40.237 | 37,44 ms | **41,28 ms** | < 300 ms | ✅ |
| Escritas (`POST /emprestimos`) | 2.710 | 242,37 ms | **264,48 ms** | < 500 ms | ✅ |

### Sobre os 409

No cenário de escrita, **1.513 de 2.710 requisições (55,8%)** receberam `409` —
e isso está correto. O cenário tem 300 usuários e cada um pode ter no máximo 3
empréstimos ativos; depois disso a regra de limite entra em ação. O k6 conta
4xx como "request failed" por padrão, por isso o número agregado de
`http_req_failed` aparece como 3,52%, mesmo com **100% dos checks passando**.

Conclusão: `http_req_failed` isolado engana neste domínio. O que importa é o
check de negócio (201 ou 409) e a latência.

---

## 3. Onde está o gargalo

### Leitura vs escrita

```
leitura  p95 =  41,28 ms
escrita  p95 = 264,48 ms   -> 6,4x mais lenta
```

A diferença não é da consulta: `GET /livros` faz um `findMany` com `_count`
(uma ida ao banco). A escrita faz, dentro de uma transação:

1. `SELECT ... FOR UPDATE` no livro (espera se outro estiver com a linha);
2. `SELECT ... FOR UPDATE` no usuário;
3. três consultas de contagem/atraso;
4. `INSERT`.

Com 10 VUs batendo no **mesmo livro**, as transações serializam. O p95 de
264 ms é o **limite superior pessimista** dessa arquitetura, não a média do
uso real (onde empréstimos se distribuem entre livros).

Isso é coerente com o ADR 0001: aceitamos serializar por livro em troca de
nunca entregar o mesmo exemplar duas vezes. Um teste com livros diferentes
mostraria p95 bem menor, mas esconderia o custo da decisão.

### Índice: antes e depois (20 mil empréstimos)

Consulta usada na disponibilidade:

```sql
SELECT count(*) FROM emprestimos
WHERE livro_id = $1 AND status = 'ATIVO';
```

| Cenário | Plano | Buffers | Tempo de execução |
| --- | --- | --- | --- |
| **Com** índice `(livro_id, status)` | Index Only Scan | 42 | **0,601 ms** |
| **Sem** o índice | Seq Scan (19.960 linhas filtradas) | 266 | **2,439 ms** |

Ganho: **~4x no tempo** e **~6,3x menos buffers** com apenas 20 mil linhas. O
índice existe no `schema.prisma` (`@@index([livroId, status])`), então já vai
junto na migration.

Consulta de atrasados usa `(status, data_prevista)`:

```
Index Scan using emprestimos_status_data_prevista_idx
Execution Time: 7,334 ms (14.990 linhas)
```

Sem esse índice, o mesmo `ORDER BY data_prevista` exigiria ordenação em
memória sobre a tabela inteira.

### O que ainda não é gargalo

- `GET /livros` com 20 VUs: p95 de 41 ms, folga grande para o SLO de 300 ms.
- O pool de conexões padrão do Prisma (2×CPU+1) não foi esgotado no teste.
- Não há N+1: a listagem usa um único `findMany` com `_count`.

---

## 4. O que eu faria diferente

Em ordem de custo/benefício:

1. **Teste com livros distintos.** Medir o cenário realista (concorrência
   distribuída) para comparar com o pior caso deste documento.
2. **Cache de `GET /livros`** com invalidação nos eventos de empréstimo e
   devolução — reduz o tráfego de leitura, que hoje é 94% das requisições.
3. **Lock por usuário** apenas para o limite de 3, se o volume justificar; hoje
   o lock do livro já resolve o risco crítico.
4. **Métricas de pool e de lock** (`pg_stat_activity`, tempo de espera) para
   separar "API lenta" de "banco saturado".

O que eu **não** faria: trocar o `FOR UPDATE` por uma coluna contador só para
melhorar o p95. O ganho não paga o risco de divergência de dados (ADR 0001).

---

## 5. Como reproduzir

```bash
# 1. subir tudo
docker compose up -d --build

# 2. smoke (dentro da rede do Compose)
docker run --rm --network cursofullcycleemprestimolivros_default \
  -e BASE_URL=http://api:3000 -v "${PWD}/k6:/scripts" \
  grafana/k6 run /scripts/smoke.js

# 3. carga (1 minuto)
docker run --rm --network cursofullcycleemprestimolivros_default \
  -e BASE_URL=http://api:3000 -v "${PWD}/k6:/scripts" \
  grafana/k6 run /scripts/load.js

# 4. experimento de índice
npm run db:seed:volume
docker exec biblioteca-db psql -U postgres -d biblioteca -c \
  "EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM emprestimos
   WHERE livro_id = '<id>' AND status = 'ATIVO';"
```

Para o passo 4, pegue um `livro_id` com muitos empréstimos:

```sql
SELECT livro_id, count(*) FROM emprestimos
WHERE status = 'ATIVO' GROUP BY 1 ORDER BY 2 DESC LIMIT 1;
```

O script `db:seed:volume` **apaga os empréstimos existentes**. Rode só no banco
local.
