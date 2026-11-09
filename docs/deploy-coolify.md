# Deploy no Coolify

Foi assim que eu publiquei a API. Precisa ter uma conta no Coolify com um
servidor conectado e o repositório no GitHub.

## 1. Criar o projeto

No Coolify, clique em **Projects → New Project** e dê um nome, por exemplo
`biblioteca`.

## 2. Criar o banco

1. **New → Database → PostgreSQL**.
2. Escolha a versão **16**.
3. Nome do serviço: `biblioteca-db`.
4. Clique em **Deploy**.
5. Abra o banco e copie a **Postgres URL (internal)**.

A URL interna é parecida com:

```
postgres://postgres:senha@biblioteca-db:5432/postgres
```

Use a interna, não a pública. A interna é mais rápida e não expõe o banco na
internet.

## 3. Criar a aplicação

1. **New → Application**.
2. Escolha o repositório `JannioFSantos/cursoFullCycleEmprestimoLivros`.
3. Branch: `main`.
4. **Build Pack: Dockerfile**.
5. Dockerfile: `/Dockerfile`.
6. Base directory: `/`.
7. Clique em **Continue**.

## 4. Variáveis de ambiente

Na aba **Environment Variables**, cadastre:

| Variável | Valor |
| --- | --- |
| `NODE_ENV` | `production` |
| `PORT` | `3000` |
| `HOST` | `0.0.0.0` |
| `LOG_LEVEL` | `info` |
| `DATABASE_URL` | a URL interna do passo 2 (marque como secret) |
| `PRAZO_DIAS` | `14` |
| `LIMITE_EMPRESTIMOS` | `3` |

O `.env` do projeto não vai para o Git. No repositório só existe o
`.env.example`.

## 5. Porta e healthcheck

- **Ports Exposes:** `3000`
- **Ports Mappings:** pode deixar vazio
- **Healthcheck:**
  - caminho: `/health`
  - porta: `3000`
  - método: `GET`
  - intervalo: `30s`

A imagem também tem um `HEALTHCHECK` no Dockerfile, que faz a mesma coisa.

## 6. Domínio

Na aba **Domains**, coloque o domínio (ou use o domínio temporário do Coolify)
e ative o **HTTPS**.

## 7. Deploy

Clique em **Deploy**. O que acontece:

1. o Coolify baixa o repositório;
2. roda o build do Dockerfile;
3. inicia o container;
4. o `scripts/entrypoint.sh` roda `prisma migrate deploy`;
5. a API começa a escutar na porta 3000.

Se a migration falhar, o container não sobe. Fiz assim de propósito: é melhor
falhar no deploy do que rodar uma API com o banco desatualizado.

## 8. Conferir se funcionou

```bash
curl -i https://seu-dominio.com/health
```

Deve voltar `200` com `{"status":"ok"}`.

Depois teste uma rota de verdade:

```bash
curl -s -X POST https://seu-dominio.com/livros \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"DDD","autor":"Eric Evans","isbn":"9780321125217","exemplaresTotal":1}'
```

## 9. Deploy automático

Com o GitHub App instalado, todo push na `main` dispara um deploy novo. Se
estiver usando repositório público, copie a **Webhook URL** do Coolify e
cadastre no GitHub em **Settings → Webhooks**.

Meu fluxo é: branch nova → pull request → CI verde → merge na main → Coolify
faz o deploy.

## 10. Migrations

Normalmente não precisa fazer nada: o entrypoint roda `prisma migrate deploy`
sozinho a cada start.

Se precisar rodar na mão:

```bash
docker exec -it <container> ./node_modules/.bin/prisma migrate deploy
```

Nunca rode `prisma migrate dev` em produção, porque ele pode apagar dados.

## Erros que podem acontecer

| Erro | Causa | O que fazer |
| --- | --- | --- |
| `P1001: Can't reach database server` | URL errada ou banco em outra rede | usar a URL interna e conferir se os dois estão no mesmo projeto |
| `P3009: failed migrations` | uma migration falhou e ficou marcada | corrigir o SQL e rodar `prisma migrate resolve --rolled-back` |
| Container reiniciando sozinho | `DATABASE_URL` faltando | ver os logs; a validação de env mostra o que falta |
| 502 Bad Gateway | API não escutou em `0.0.0.0:3000` | conferir `HOST`, `PORT` e a porta exposta |
| Healthcheck falhando | banco fora ou migration pendente | abrir `/health`; se der 503, o problema é o banco |
| Build lento | `npm ci` sem cache | o Dockerfile já copia o `package.json` antes do código |

## Segurança

- senhas só no Coolify, marcadas como secret;
- o `.env.example` não tem senha real;
- o banco não precisa de porta pública;
- ative o backup automático do PostgreSQL;
- o container roda como usuário `node`, não como root.
