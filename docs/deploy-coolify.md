# Deploy no Coolify — passo a passo

Este é o guia que usei para publicar a API. Ele assume que você já tem uma
instância do Coolify com um servidor conectado e o repositório no GitHub.

> **Resumo:** 1 banco PostgreSQL + 1 aplicação com build pack **Dockerfile**.
> As migrations rodam sozinhas no start do container. Nenhum segredo fica no
> repositório.

---

## Antes de começar

- repositório: `https://github.com/JannioFSantos/cursoFullCycleEmprestimoLivros`
- branch de produção: `main`
- a imagem expõe a porta **3000**
- healthcheck: `GET /health` na porta 3000

---

## 1. Criar o projeto

No Coolify: **Projects → + Add → New Project**.
Dê um nome (ex.: `biblioteca`) e abra o projeto.

Dentro dele você vai criar **dois recursos**: o banco e a aplicação.

---

## 2. Criar o PostgreSQL

1. **+ New → Database → PostgreSQL**.
2. Versão: **16** (a mesma do `docker-compose.yml`).
3. Nome do serviço: `biblioteca-db` (evite acentos e espaços).
4. **Deploy**.
5. Quando ficar verde, abra o recurso e copie a **Postgres URL (internal)**.

Ela se parece com:

```
postgres://postgres:senha-gerada@biblioteca-db:5432/postgres
```

> **Use a URL interna.** A URL pública (`...@147.x.x.x:5432`) funciona, mas
> expõe o banco à internet e é mais lenta. Interna é o padrão correto.

Guarde também usuário, senha e nome do banco: você vai precisar deles se
precisar rodar comando manual.

---

## 3. Criar a aplicação

1. **+ New → Application**.
2. Fonte: **GitHub App** (recomendado) ou **Public Repository**.
3. Selecione `JannioFSantos/cursoFullCycleEmprestimoLivros`.
4. Branch: `main`.
5. **Build Pack: Dockerfile**.
6. Dockerfile location: `/Dockerfile` (raiz do repositório).
7. Base directory: `/`.
8. **Continue**.

---

## 4. Variáveis de ambiente

Na aba **Environment Variables**, cadastre:

| Variável | Valor | Observação |
| --- | --- | --- |
| `NODE_ENV` | `production` | liga o log JSON |
| `PORT` | `3000` | precisa bater com a porta exposta |
| `HOST` | `0.0.0.0` | obrigatório em container |
| `LOG_LEVEL` | `info` | use `debug` só para investigar |
| `DATABASE_URL` | a URL interna do passo 2 | marque como **secret** |
| `PRAZO_DIAS` | `14` | regra de negócio |
| `LIMITE_EMPRESTIMOS` | `3` | regra de negócio |

Regras práticas:

- **Nunca** suba o `.env` para o Git. O que está no repositório é só o
  `.env.example`.
- Variável marcada como *secret* não aparece nos logs do build.
- Se trocar a senha do banco no Coolify, atualize a `DATABASE_URL` e faça
  redeploy.

---

## 5. Rede, porta e healthcheck

Na aba **Configuration → Network** (ou **General**):

- **Ports Exposes:** `3000`
- **Ports Mappings:** deixe vazio (o proxy do Coolify cuida do acesso)
- **Healthcheck:**
  - Enable: sim
  - Path: `/health`
  - Port: `3000`
  - Method: `GET`
  - Interval: `30s`
  - Timeout: `5s`
  - Retries: `3`

A imagem também tem um `HEALTHCHECK` no Dockerfile. Manter os dois alinhados
evita o Coolify derrubar o container por um critério diferente do Docker.

---

## 6. Domínio e HTTPS

Na aba **Domains**:

1. informe o domínio (ex.: `biblioteca.seudominio.com`);
2. aponte o DNS do domínio para o IP do servidor do Coolify;
3. ative **HTTPS** (Let's Encrypt);
4. salve.

Se ainda não tem domínio, use o domínio temporário gerado pelo Coolify
(`*.sslip.io`) para validar.

---

## 7. Deploy

Clique em **Deploy**. O que acontece:

1. o Coolify clona o repositório;
2. roda o build multi-stage do Dockerfile (`npm ci` + `tsc`);
3. inicia o container;
4. o `scripts/entrypoint.sh` executa:
   ```bash
   ./node_modules/.bin/prisma migrate deploy
   node dist/server.js
   ```
5. o healthcheck chama `/health`, que também consulta o banco.

Acompanhe em **Logs**. A primeira linha relevante é:

```json
{"level":30,"msg":"api_iniciada","porta":3000,"ambiente":"production"}
```

Se a migration falhar, o container **não sobe**. Isso é intencional: melhor
falhar no deploy do que servir uma API incompatível com o banco.

---

## 8. Validar

```bash
curl -i https://biblioteca.seudominio.com/health
# 200 {"status":"ok","uptimeSegundos":12}

curl -s https://biblioteca.seudominio.com/ | jq
curl -s https://biblioteca.seudominio.com/metrics | head
```

Fluxo real:

```bash
curl -s -X POST https://biblioteca.seudominio.com/livros \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"DDD","autor":"Eric Evans","isbn":"9780321125217","exemplaresTotal":1}'
```

---

## 9. Deploy automático

Com **GitHub App**, todo push na `main` dispara um novo deploy.
Se estiver usando repositório público sem a App, copie a **Webhook URL** do
Coolify e cadastre em **GitHub → Settings → Webhooks**, com o segredo exibido.

Sugestão de fluxo:

```
feature/* -> Pull Request -> CI verde -> merge na main -> Coolify deploy
```

O CI (`lint`, testes, build da imagem) roda antes; o Coolify só recebe código
que passou.

---

## 10. Migrations em produção

- Automático: `prisma migrate deploy` no entrypoint.
- Manual (se precisar):
  ```bash
  docker exec -it <container> ./node_modules/.bin/prisma migrate deploy
  ```
  ou pelo terminal do Coolify.
- **Nunca** rode `prisma migrate dev` em produção: ele pode resetar dados.
- Migrations são **forward-only**. Para reverter, faça um novo deploy de um
  commit anterior **e** uma migration de correção — não edite migration já
  aplicada.

---

## Erros comuns e o que fazer

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `P1001: Can't reach database server` | usou URL pública ou banco em outra rede | use a **URL interna** e confirme que os dois recursos estão no mesmo projeto/rede |
| `P3009: failed migrations` | uma migration falhou e ficou registrada | corrija o SQL, `prisma migrate resolve --rolled-back <nome>` e redeploy |
| Container sobe e morre em 1s | `DATABASE_URL` ausente/inválida | veja os logs; a validação de env mata o processo com mensagem clara |
| 502 Bad Gateway | API não escutou em `0.0.0.0:3000` | confira `HOST`, `PORT` e **Ports Exposes** |
| Healthcheck falhando | banco fora ou migration pendente | abra `/health`; 503 significa banco, não API |
| `PrismaClientInitializationError` | falta `openssl` na imagem | o Dockerfile já instala; se mudou a base, mantenha |
| Build lento | `npm ci` sem cache | o Dockerfile copia `package*.json` antes do código |

---

## Segurança

- Segredos só no Coolify (aba Environment), marcados como secret.
- O `.env.example` não contém senha real.
- O banco não precisa de porta pública; desative o acesso externo se não for
  usar.
- Ative backup automático do PostgreSQL no Coolify.
- O container roda como usuário `node` (não-root).
- `authorization` e `cookie` são removidos dos logs via `redact`.

---

## Escala (o que muda quando crescer)

O projeto foi desenhado para **uma instância**. Se precisar escalar:

1. O `SELECT ... FOR UPDATE` continua correto com N instâncias, porque a
   exclusão mútua está no PostgreSQL.
2. As métricas são em memória por processo. Com N réplicas, use um Prometheus
   com `scrape` em cada instância (ou um agente) em vez de ler `/metrics` de
   um único container.
3. O rate limit (se entrar) precisa de armazenamento compartilhado.

Nada disso é necessário para o escopo do Projeto B — está aqui para mostrar que
a limitação é conhecida.
