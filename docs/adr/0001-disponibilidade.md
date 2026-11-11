# ADR 0001 — Como impedir que o último exemplar seja emprestado duas vezes

- **Status:** aceito
- **Data:** 05/11/2026
- **Autor:** Jannio Ferreira dos Santos

## O problema

Um livro pode ter vários exemplares. A regra é: só empresta se
`empréstimos ativos < exemplares totais`.

O jeito mais óbvio de fazer isso é:

1. contar os empréstimos ativos;
2. ver se ainda tem exemplar;
3. inserir o empréstimo.

O problema é quando duas pessoas fazem isso ao mesmo tempo. As duas contam
antes de qualquer uma inserir, as duas veem que tem 1 exemplar, e as duas
inserem. No fim, o mesmo exemplar foi emprestado duas vezes.

Isso não acontece em teste manual, só com requisições simultâneas. Por isso
precisa de uma decisão.

## Opções que eu considerei

**1. Guardar uma coluna `exemplares_disponiveis` no livro**

A ideia é diminuir esse número a cada empréstimo. Descartei porque vira uma
segunda fonte de verdade: se uma devolução falhar ou alguém mexer no banco, o
número fica errado e não tem como saber qual está certo. Além disso, ainda
precisa de um `UPDATE` com condição para evitar a corrida.

**2. Usar um lock no Redis**

Resolve, mas eu teria que adicionar Redis só para isso. Para o tamanho do
projeto não vale a pena. Também tem casos chatos, como o lock ficar preso se
um processo morrer.

**3. Índice único em `livro_id` para empréstimos ativos**

Não funciona porque impediria o segundo empréstimo mesmo quando o livro tem
vários exemplares.

**4. Transação com `SELECT ... FOR UPDATE` (escolhida)**

Travar a linha do livro antes de contar. Enquanto uma transação está com a
linha travada, a outra espera. Quando a primeira termina, a segunda conta de
novo e aí sim decide.

## A decisão

Dentro de uma transação, eu travo a linha do livro com SQLAlchemy:

```python
livro = sessao.execute(
    select(LivroModelo)
    .where(
        LivroModelo.id == dados.livro_id,
        LivroModelo.excluido_em.is_(None),
    )
    .with_for_update()
).scalar_one_or_none()
```

O SQL gerado é o mesmo de antes:

```sql
SELECT id, exemplares_total
FROM livros
WHERE id = $1 AND excluido_em IS NULL
FOR UPDATE;
```

Depois conto os empréstimos ativos, valido as regras e insiro. Se a validação
falhar, a transação é desfeita e a API responde `409`.

Também travo a linha do usuário, sempre **depois** do livro. Mantenho essa
ordem em todas as transações para evitar deadlock (duas transações esperando
uma pela outra). A transação usa `SET LOCAL lock_timeout = '10s'`: se a espera
por um lock passar de 10 segundos, o PostgreSQL aborta em vez de segurar a
requisição para sempre.

A validação continua em uma função pura (`validar_emprestimo`, em
`app/domain/regras.py`), que é a mesma usada nos testes unitários. O
repositório (`app/infra/repositorios.py`, método `criar_com_bloqueio`) só
chama essa função dentro da transação.

## O que muda com isso

**Bom:**

- se duas pessoas pedirem o último exemplar juntas, uma recebe `201` e a outra
  `409`;
- não precisei adicionar Redis nem outra infraestrutura;
- a regra continua testável sem banco;
- a mesma função de validação roda nos testes unitários e em produção.

**Ruim:**

- pedidos para o mesmo livro ficam em fila, um esperando o outro. No teste de
  carga isso apareceu: a escrita ficou com p95 de 150 ms, contra 85 ms da
  leitura. Está em `docs/desempenho.md`;
- quem for mexer nesse arquivo precisa entender transação e SQL. Por isso
  deixei o código bem comentado;
- um livro muito disputado pode virar gargalo. É o preço de não emprestar o
  mesmo exemplar duas vezes.

## Como conferir

- Teste de integração: dois empréstimos do único exemplar, o segundo recebe
  `409 LIVRO_INDISPONIVEL`.
- Teste de carga: o cenário de escrita mede o p95 nesse cenário de disputa.
- Logs: cada requisição mostra `duracaoMs`, então dá para ver se o tempo está
  na API ou na espera do banco.
