# Uso de IA

O curso permitiu usar IA, então usei. A regra que tentei seguir foi: a decisão
é minha e eu preciso saber explicar o código. Este arquivo é para registrar o
que a IA ajudou e o que eu mudei.

## O que eu pedi

**1. Ideia do projeto**

Pedi uma sugestão de domínio para o Projeto B, com um fluxo principal e regras
que desse para testar sem precisar de muita infraestrutura. A sugestão foi
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

**4. Deploy**

Pedi os passos para publicar Node + Prisma + PostgreSQL no Coolify e como rodar
migration no start do container. Aprendi o `prisma migrate deploy` no
entrypoint e a importância do `HOST=0.0.0.0`.

## O que eu conferi

- Gerei e revisei as migrations antes de commitar.
- Rodei todos os comandos do README.
- Rodei os testes e o k6 e usei os números que saíram, não estimativa.
- Li o código até entender cada parte que ficou no projeto.

## O que eu não sei explicar ainda

- Configurar o Prometheus e o Grafana para ler o `/metrics`.
- Fazer deploy com mais de uma instância.

Deixei esses pontos de fora do escopo para não entregar coisa que eu não
consigo defender na apresentação.
