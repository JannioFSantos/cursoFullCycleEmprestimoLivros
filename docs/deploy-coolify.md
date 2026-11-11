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

A aplicação aceita a URL nos formatos `postgres://` e `postgresql://`. Na
inicialização ela troca o driver para `postgresql+psycopg://`, que é o que o
SQLAlchemy + psycopg 3 esperam. Não precisa editar a URL copiada do Coolify.

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
| `APP_ENV` | `production` |
| `PORT` | `3000` |
| `HOST` | `0.0.0.0` |
| `LOG_LEVEL` | `info` |
| `DATABASE_URL` | a URL interna do passo 2 (marque como secret) |
| `SECRET_KEY` | valor aleatório, marcado como secret |
| `PRAZO_DIAS` | `14` |
| `LIMITE_EMPRESTIMOS` | `3` |

`SECRET_KEY` assina o cookie de sessão usado pelas mensagens `flash` da tela
de demonstração. Em produção, gere um valor aleatório; o padrão do código serve
só para desenvolvimento.

O `.env` do projeto não vai para o Git. No repositório só existe o
`.env.example`. Se você já tinha o ambiente antigo configurado com `NODE_ENV`,
ele continua sendo aceito, mas o nome novo é `APP_ENV`.

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

Na aba **Domains**, coloque `agendadeconsultas.v6.rocks` e ative o **HTTPS**.

## 7. Deploy

Clique em **Deploy**. O que acontece:

1. o Coolify baixa o repositório;
2. roda o build do Dockerfile;
3. inicia o container;
4. o `scripts/entrypoint.sh` roda `alembic upgrade head`;
5. o Gunicorn começa a escutar na porta 3000.

Se a migration falhar, o container não sobe. Fiz assim de propósito: é melhor
falhar no deploy do que rodar uma API com o banco desatualizado.

## 8. Conferir se funcionou

```bash
curl -i https://agendadeconsultas.v6.rocks/health
```

Deve voltar `200` com `{"status":"ok", ...}`. Se o banco estiver fora, a rota
responde `503` com `{"status":"degradado","banco":"indisponivel"}`.

A tela de demonstração fica em `https://agendadeconsultas.v6.rocks/`.
A documentação Swagger fica em `https://agendadeconsultas.v6.rocks/API/docs`.
Ela lê o `docs/openapi.yaml` que vai junto na imagem Docker.

Depois teste uma rota de verdade:

```bash
curl -s -X POST https://agendadeconsultas.v6.rocks/API/livros \
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

Normalmente não precisa fazer nada: o entrypoint roda `alembic upgrade head`
sozinho a cada start. O comando é idempotente e só aplica o que ainda não foi
aplicado.

Se precisar rodar na mão:

```bash
docker exec -it <container> alembic upgrade head
```

Para ver o histórico:

```bash
docker exec -it <container> alembic current
docker exec -it <container> alembic history
```

Evite rodar `alembic downgrade` em produção, porque ele desfaz alterações de
schema e pode apagar dados.

## Erros que podem acontecer

| Erro | Causa | O que fazer |
| --- | --- | --- |
| `psycopg.OperationalError: connection failed` | URL errada ou banco em outra rede | usar a URL interna e conferir se os dois estão no mesmo projeto |
| `could not translate host name` | o host da URL não é o nome do serviço do banco | copiar de novo a URL interna do PostgreSQL |
| `Target database is not up to date` | a aplicação subiu sem aplicar migration | rodar `alembic upgrade head` no container |
| Container reiniciando sozinho | `DATABASE_URL` faltando ou inválida | ver os logs; a validação de configuração mostra o que falta |
| `502 Bad Gateway` | API não escutou em `0.0.0.0:3000` | conferir `HOST`, `PORT` e a porta exposta |
| Healthcheck falhando | banco fora ou migration pendente | abrir `/health`; se der 503, o problema é o banco |
| Build lento | dependências sendo reinstaladas | o Dockerfile copia `requirements.txt` antes do código, então o cache só é invalidado quando as dependências mudam |

## Segurança

- senhas só no Coolify, marcadas como secret;
- o `.env.example` não tem senha real;
- o banco não precisa de porta pública;
- ative o backup automático do PostgreSQL;
- o container roda como usuário `app` (uid 10001), não como root.
