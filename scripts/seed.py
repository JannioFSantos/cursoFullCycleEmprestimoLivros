"""Cadastra dados de exemplo para abrir a tela e brincar com a API.

Idempotente: se o ISBN/e-mail já existir, ele não duplica. Rodar:

    python -m scripts.seed

Precisa do banco de pé e das migrações aplicadas (`alembic upgrade head`).
"""

from __future__ import annotations

from sqlalchemy import select

from app.config import carregar_configuracao
from app.infra.banco import criar_engine, criar_session_factory
from app.infra.modelos import LivroModelo, UsuarioModelo, agora_utc

LIVROS = [
    ("Código Limpo", "Robert C. Martin", "9788576082675", 3),
    ("Arquitetura Limpa", "Robert C. Martin", "9788550804606", 3),
    ("O Programador Pragmático", "Andrew Hunt e David Thomas", "9788582605407", 2),
    ("Refatoração", "Martin Fowler", "9788577804130", 2),
    ("Domain-Driven Design", "Eric Evans", "9780321125217", 2),
    (
        "Padrões de Projeto",
        "Erich Gamma, Richard Helm, Ralph Johnson e John Vlissides",
        "9788577807006",
        1,
    ),
    ("Entendendo Algoritmos", "Aditya Bhargava", "9788575225639", 2),
    ("Use a Cabeça! Python", "Paul Barry", "9788576081746", 1),
    ("Docker em Ação", "Jeff Nickoloff", "9788575225093", 1),
    ("Kubernetes em Ação", "Marko Lukša", "9788575227056", 1),
]

USUARIOS = [
    ("Ana Souza", "ana@exemplo.com"),
    ("Bruno Lima", "bruno@exemplo.com"),
    ("Carla Dias", "carla@exemplo.com"),
    ("Diego Alves", "diego@exemplo.com"),
    ("Elisa Rocha", "elisa@exemplo.com"),
]


def executar() -> None:
    configuracao = carregar_configuracao()
    motor = criar_engine(configuracao.database_url)
    sessao = criar_session_factory(motor)

    criados = 0
    with sessao() as banco:
        for titulo, autor, isbn, exemplares in LIVROS:
            existe = banco.scalar(
                select(LivroModelo.id).where(LivroModelo.isbn == isbn)
            )
            if existe:
                continue
            banco.add(
                LivroModelo(
                    titulo=titulo,
                    autor=autor,
                    isbn=isbn,
                    exemplares_total=exemplares,
                    criado_em=agora_utc(),
                )
            )
            criados += 1

        for nome, email in USUARIOS:
            existe = banco.scalar(
                select(UsuarioModelo.id).where(UsuarioModelo.email == email)
            )
            if existe:
                continue
            banco.add(
                UsuarioModelo(nome=nome, email=email, criado_em=agora_utc())
            )
            criados += 1

        banco.commit()

    motor.dispose()
    print(f"Seed concluído: {criados} registro(s) novo(s).")


if __name__ == "__main__":
    executar()
