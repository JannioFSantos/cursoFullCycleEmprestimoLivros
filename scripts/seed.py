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
    ("Dom Casmurro", "Machado de Assis", "9788535910663", 3),
    ("Grande Sertão: Veredas", "João Guimarães Rosa", "9788520925152", 2),
    ("Vidas Secas", "Graciliano Ramos", "9788503012039", 2),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", "9788594318606", 1),
    ("O Cortiço", "Aluísio Azevedo", "9788508042741", 2),
    ("Capitães da Areia", "Jorge Amado", "9788535911691", 1),
    ("A Hora da Estrela", "Clarice Lispector", "9788520932389", 2),
    ("Sagarana", "João Guimarães Rosa", "9788520923547", 1),
    ("Quarto de Despejo", "Carolina Maria de Jesus", "9788508172868", 1),
    ("Torto Arado", "Itamar Vieira Junior", "9788580556267", 4),
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
