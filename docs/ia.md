# Uso de IA

O curso permitiu usar IA, então usei. A regra que tentei seguir foi: a decisão
é minha e eu preciso saber explicar o código. Este arquivo é para registrar o
que a IA ajudou e o que eu mudei.

## O que eu pedi

**1. Ideia do projeto**

Pedi uma sugestão de domínio para o Projeto B, com um fluxo principal e regras
que dessem para testar sem precisar de muita infraestrutura. A sugestão foi
biblioteca, com empréstimo e devolução. Gostei porque é fácil de explicar e tem
a regra do último exemplar.

**2. A parte da concorrência**

Pedi para explicar por que uma coluna `exemplares_disponiveis` é pior do que
contar os empréstimos ativos dentro de uma transação. Também pedi alternativas
para colocar no ADR.

Aceitei a comparação e a ideia de travar primeiro o livro e depois o usuário,
para evitar deadlock. Recusei usar Redis, porque não fazia sentido para o
tamanho do projeto.

**3. Testes**

Pedi uma lista de casos de teste para as três regras de empréstimo. Também
pedi ajuda para testar atraso sem esperar 14 dias. A ideia do relógio trocável
veio daí.

**4. Migração para Python**

Pedi ajuda para portar o projeto de TypeScript/Node/Fastify/Prisma para
Python/Flask. A IA propôs a estrutura com `domain`, `use_cases`, `infra`,
`http` e `observabilidade`, usando SQLAlchemy 2.0, Alembic, Pydantic v2 e
pytest. Aceitei a estrutura porque era a mesma separação de camadas que eu já
tinha, só que em Python.

Também pedi ajuda para:

- trocar o k6 pelo Locust, com os mesmos cenários de leitura e escrita;
- escrever a tela de demonstração com Jinja, sem JavaScript;
- adaptar o `Dockerfile` para Gunicorn e criar o `entrypoint.sh` com
  `alembic upgrade head`;
- revisar as mensagens de erro e os códigos da API para não mudar o contrato.

**5. Deploy**

Pedi os passos para publicar Flask + SQLAlchemy + PostgreSQL no Coolify e como
rodar migration no start do container. Aprendi a usar `alembic upgrade head`
no entrypoint e a importância do `HOST=0.0.0.0`.

## O que eu conferi

- Gerei e revisei as migrations do Alembic antes de commitar.
- Rodei todos os comandos do README.
- Rodei os testes e o Locust e usei os números que saíram, não estimativa.
- Comparei as respostas da API Python com o contrato `docs/openapi.yaml` e com
  a versão TypeScript, para garantir que status, códigos de erro e formato das
  datas continuassem iguais.
- Li o código até entender cada parte que ficou no projeto.

## O que eu não sei explicar ainda

- Configurar o Prometheus e o Grafana para ler o `/metrics`.
- Fazer deploy com mais de uma instância.

Deixei esses pontos de fora do escopo para não entregar coisa que eu não
consigo defender na apresentação.
