# ADR 0002 — Excluir cadastro sem apagar o histórico

- **Status:** aceito
- **Data:** 09/11/2026
- **Autor:** Jannio Ferreira dos Santos

## O problema

A biblioteca precisa poder tirar do catálogo um livro que não existe mais e
tirar da lista um usuário que não usa mais o serviço.

O jeito mais simples seria `DELETE FROM livros WHERE id = ...`. Só que a
tabela `emprestimos` aponta para `livros` e `usuarios`. Se eu apagar a linha,
o histórico de quem pegou o livro some junto (ou o banco recusa por causa da
chave estrangeira).

Histórico apagado é problema para a biblioteca: não dá mais para saber quem
pegou qual livro, nem responder a uma cobrança antiga.

## Opções que eu considerei

**1. Apagar em cascata (`ON DELETE CASCADE`)**

Apagaria o livro e todos os empréstimos dele. É simples, mas joga fora
justamente a informação que a biblioteca precisa guardar. Descartei.

**2. Bloquear a exclusão quando existe empréstimo (`409`)**

Foi a primeira versão que fiz. Preserva o histórico, mas deixa a tela travada:
o livro que não existe mais fica no catálogo para sempre. Descartei.

**3. Exclusão lógica (escolhida)**

Criar uma coluna `excluido_em` (data e hora) nas tabelas `livros` e `usuarios`.

- Sem empréstimo: apago a linha de verdade, porque não há histórico a guardar.
- Com empréstimo: não apago. Só preencho `excluido_em`.

As consultas de catálogo e de lista passam a filtrar `excluido_em IS NULL`.
Assim o cadastro desaparece da tela, mas a linha continua no banco e o
empréstimo antigo continua conseguindo mostrar o título e o nome.

## A decisão

1. A regra pura `decidir_modo_de_exclusao(emprestimos_registrados)` fica em
   `app/domain/regras.py` e devolve `ModoDeExclusao.APAGAR` ou
   `ModoDeExclusao.MANTER_HISTORICO`.
2. O repositório SQLAlchemy faz a contagem e a gravação na mesma transação,
   com `with_for_update()`. Isso evita que um empréstimo novo entre no meio.
3. O caso de uso passa a data da exclusão usando o `Relogio` injetado, do
   mesmo jeito que a devolução faz.
4. A API continua respondendo `204`. O cliente não precisa saber se a linha
   foi apagada ou marcada.
5. A tela mostra uma página de confirmação somente quando existe empréstimo,
   avisando que o histórico será mantido. Sem histórico, a exclusão é direta.

## O que muda com isso

**Bom:**

- o histórico de empréstimos nunca é apagado;
- o cadastro sai da tela e não pode mais ser usado em empréstimo novo;
- a API continua simples: um `DELETE` e um `204`;
- a regra fica testável sem banco.

**Ruim:**

- as consultas de lista precisam lembrar do filtro `excluido_em IS NULL`;
- ISBN e e-mail de um cadastro excluído continuam únicos no banco. Se quiser
  cadastrar de novo o mesmo ISBN/e-mail, é preciso usar outro valor;
- a tela precisa mostrar a etiqueta "excluído" no histórico.

## Como conferir

- Teste unitário: `decidir_modo_de_exclusao(0)` devolve `APAGAR` e
  `decidir_modo_de_exclusao(1)` devolve `MANTER_HISTORICO`.
- Teste de integração: excluir livro/usuário com empréstimo devolve `204`, o
  cadastro some de `GET /API/livros` ou `GET /API/usuarios`, mas continua em
  `GET /API/emprestimos` com `excluidoEm` preenchido.
- Teste de integração: tentar emprestar para um livro/usuário excluído devolve
  `404`.
