# ADR 0001 — Como impedir o empréstimo duplicado do último exemplar

- **Status:** aceito
- **Data:** 2026-11-05
- **Decisores:** Jannio Ferreira dos Santos
- **Contexto do curso:** Full Cycle — Módulo 4 — Projeto B

## Contexto e problema

A biblioteca pode ter mais de um exemplar do mesmo livro. A regra é simples:
não é possível emprestar um livro quando `empréstimos ativos >= exemplares
totais`.

O problema aparece com **duas requisições simultâneas** para o último
exemplar. O fluxo ingênuo é:

1. contar empréstimos ativos;
2. verificar se ainda há exemplar;
3. inserir o empréstimo.

Se as duas requisições executam o passo 1 antes de qualquer uma executar o
passo 3, as duas veem "1 exemplar disponível" e as duas inserem. Resultado:
dois empréstimos para um exemplar só.

Esse é um problema de **corrida crítica** (race condition) e não aparece em
teste manual. É preciso decidir onde a exclusão mútua acontece.

## Alternativas consideradas

### Alternativa A — Coluna `exemplares_disponiveis` no livro (descartada)

Manter um contador desnormalizado, decrementando com `UPDATE ... SET
disponiveis = disponiveis - 1 WHERE disponiveis > 0`.

**Por que foi descartada:**
- cria uma segunda fonte de verdade: o contador pode divergir da contagem real
  de empréstimos (bug de devolução, importação, correção manual);
- continua sendo necessário um `UPDATE` condicional para evitar corrida, então
  não elimina a complexidade — apenas a esconde;
- qualquer relatório precisa reconciliar dois números.

### Alternativa B — Lock distribuído no Redis (descartada)

Adquirir um lock por `livroId` antes de contar.

**Por que foi descartada:**
- adiciona um componente de infraestrutura (Redis) para resolver um problema
  que o banco já resolve;
- lock distribuído tem seus próprios casos de borda (TTL, processo que morre
  segurando o lock);
- o volume do projeto não justifica.

### Alternativa C — Transação + `SELECT ... FOR UPDATE` (escolhida)

Dentro de uma transação, travar a linha do livro antes de contar.

**Por que foi escolhida:**
- o próprio PostgreSQL garante a exclusão mútua;
- a fonte de verdade continua sendo a contagem de empréstimos;
- não adiciona infraestrutura;
- o custo é conhecido e mensurável: quem chega depois espera o commit de quem
  chegou antes.

### Alternativa D — Constraint única parcial (descartada)

Criar um índice único em `(livro_id)` para empréstimos ativos.

**Por que foi descartada:** impediria **qualquer** segundo empréstimo do mesmo
livro, mesmo quando há vários exemplares. Não modela a regra real.

## Decisão

Usar **transação com `SELECT ... FOR UPDATE`** na linha do livro, sempre antes
de qualquer contagem:

```sql
BEGIN;
SELECT id, exemplares_total FROM livros WHERE id = $1 FOR UPDATE;
-- com a linha travada, contar e validar é seguro
SELECT count(*) FROM emprestimos WHERE livro_id = $1 AND status = 'ATIVO';
INSERT INTO emprestimos (...) VALUES (...);
COMMIT;
```

A validação permanece no domínio, como função pura
(`validarEmprestimo`), e o repositório apenas a invoca dentro da transação.
Assim a regra é testável sem banco e a atomicidade fica no banco.

### Detalhe: ordem dos locks

Também travamos a linha do usuário, sempre **depois** do livro. Manter a mesma
ordem em todas as transações evita deadlock (duas transações esperando uma pela
outra). O PostgreSQL detecta deadlock e aborta uma delas; evitar a situação é
melhor do que tratar o erro.

### Limitação assumida (e documentada)

O limite de 3 empréstimos e o bloqueio por atraso também são checados dentro da
mesma transação, com o usuário travado. Ainda assim, **preferimos não
serializar todas as requisições do mesmo usuário em cenários de altíssima
concorrência**: o lock do livro já resolve o risco crítico (último exemplar).
Se o volume crescer, o próximo passo é um lock por usuário ou uma constraint
de negócio mais forte — e um novo ADR.

## Consequências

**Positivas**
- dois pedidos simultâneos do último exemplar resultam em **um 201 e um 409**
  (coberto pelo teste de integração e pelo teste de carga);
- nenhuma infraestrutura extra;
- a regra continua em uma função pura e testável.

**Negativas**
- requisições para o **mesmo livro** são serializadas; o p95 de escrita sobe
  sob concorrência concentrada (medido em `docs/desempenho.md`);
- o desenvolvedor precisa conhecer transação e SQL cru para mexer nesse
  arquivo — por isso ele está comentado linha a linha.

## Como verificar

1. Teste de integração: dois empréstimos do único exemplar -> segundo recebe
   `409 LIVRO_INDISPONIVEL`.
2. Teste de carga (`k6/load.js`): o cenário de escritas registra p95 e a
   taxa de respostas de negócio.
3. Logs estruturados mostram `duracaoMs` por requisição, permitindo identificar
   se o tempo está no lock.
