# Roteiro de apresentação (10 minutos)

> Apresentação é opcional, mas conta bônus. Este roteiro segue exatamente a
> sugestão da aula: 1 min problema/nível, 3 min demo, 3 min decisão técnica,
> 3 min números e próximos passos.

## Antes de começar (checklist de 2 minutos)

```bash
docker compose up -d --build
curl http://localhost:3000/health
```

Deixe abertos:
- terminal na pasta do projeto;
- navegador em `http://localhost:3000` (mostra as rotas);
- `docs/openapi.yaml` ou Swagger Editor;
- arquivo `docs/desempenho.md`;
- GitHub Actions com o pipeline verde.

## 0:00–1:00 — Problema e nível

Fala sugerida:

> "Uma biblioteca precisa controlar empréstimo e devolução de exemplares. O
> problema de verdade não é CRUD: é impedir que duas pessoas levem o mesmo
> último exemplar ao mesmo tempo. Escolhi o **Projeto B** porque preferi
> entregar um fluxo pequeno com todas as camadas provadas, em vez de um
> marketplace pela metade."

Mostre no README a primeira linha: `Nível: Projeto B`.

## 1:00–4:00 — Demonstração

> **Dica:** os comandos usam `jq` para formatar o JSON. Se ele não estiver
> instalado, remova o `| jq` — a resposta aparece em uma linha só e continua
> válida para a demo.

Rode os comandos, explicando em voz alta o que cada resposta significa.

```bash
# 1. catálogo com disponibilidade calculada
curl -s http://localhost:3000/livros | jq

# 2. cadastrar livro com 1 exemplar
curl -s -X POST http://localhost:3000/livros \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"DDD","autor":"Eric Evans","isbn":"9780321125217","exemplaresTotal":1}'

# 3. cadastrar usuário
curl -s -X POST http://localhost:3000/usuarios \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Ana","email":"ana@exemplo.com"}'

# 4. emprestar (201)
curl -s -X POST http://localhost:3000/emprestimos \
  -H 'Content-Type: application/json' \
  -d '{"livroId":"<ID>","usuarioId":"<ID>"}'
```

Agora o momento que importa:

```bash
# 5. outro usuário tentando o mesmo exemplar -> 409 LIVRO_INDISPONIVEL
curl -s -X POST http://localhost:3000/emprestimos \
  -H 'Content-Type: application/json' \
  -d '{"livroId":"<ID>","usuarioId":"<OUTRO_ID>"}'

# 6. devolver e emprestar de novo
curl -s -X PATCH http://localhost:3000/emprestimos/<ID>/devolucao

# 7. métricas
curl -s http://localhost:3000/metrics | grep emprestimos_total
```

Mensagem para fechar o bloco:

> "O 409 não é falha: é a regra funcionando. E o teste de integração prova
> exatamente esse caminho."

## 4:00–7:00 — Uma decisão e a alternativa descartada

Abra `docs/adr/0001-disponibilidade.md` e resuma:

> "O fluxo ingênuo é contar, verificar e inserir. Com duas requisições
> simultâneas, as duas contam antes de qualquer inserção e as duas passam.
>
> Eu poderia manter uma coluna `exemplares_disponiveis`. Descartei porque cria
> uma segunda fonte de verdade que desvia e não elimina a corrida.
>
> Também poderia usar um lock no Redis. Descartei porque adiciona
> infraestrutura para um problema que o banco resolve.
>
> A decisão foi travar a linha do livro com `SELECT ... FOR UPDATE` dentro de
> uma transação. Quem chega depois espera o commit. A regra continua em uma
> função pura, e o teste de integração prova que o segundo pedido recebe 409."

Se perguntarem sobre o custo:

> "O custo é serializar pedidos do mesmo livro. Está medido: o p95 de escrita
> é X ms com 10 VUs, contra Y ms de leitura. Está em `docs/desempenho.md`."

## 7:00–10:00 — Números e o que faria diferente

Mostre `docs/desempenho.md`:

- p95 de leitura e escrita;
- taxa de checks;
- onde estava o gargalo;
- o que foi feito (ou por que não foi).

Frase de fechamento:

> "O que eu faria diferente com mais tempo: [escolha uma]
> 1. um lock por usuário para o limite de 3 empréstimos;
> 2. cache de `GET /livros` com invalidação no empréstimo;
> 3. painel no Grafana consumindo `/metrics`.
>
> O que eu não faria: aumentar o escopo. O Projeto B só vale se o fluxo
> inteiro funcionar."

## Perguntas prováveis (e respostas curtas)

| Pergunta | Resposta |
| --- | --- |
| Por que não usar `SERIALIZABLE`? | Aumentaria o custo e os retries; `FOR UPDATE` resolve o ponto exato de disputa. |
| O que acontece se o processo morrer no meio? | A transação não commitada é desfeita pelo PostgreSQL. |
| Por que UUID e não id numérico? | Não expõe volume e permite gerar id antes do insert. |
| Como o Coolify sabe que está saudável? | `HEALTHCHECK` na imagem chamando `/health`, que também testa o banco. |
| Onde estão os segredos? | Só no painel do Coolify; o repositório tem apenas `.env.example`. |
| Cobertura de 90% é real? | É medida em `src/domain` e `src/use-cases`, que é onde ficam as regras. O número não inclui rotas. |
