"""Gera volume de empréstimos para medir o efeito dos índices.

Cria (se faltar) 40 livros e 200 usuários e APAGA todos os empréstimos antes de
inserir 20.000 novos, espalhados entre eles. Use só no banco local.

    python -m scripts.seed_volume

Depois, para comparar com/sem índice:

    DROP INDEX emprestimos_livro_id_status_idx;
    EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM emprestimos
      WHERE livro_id = '<id>' AND status = 'ATIVO';
    CREATE INDEX emprestimos_livro_id_status_idx
      ON emprestimos (livro_id, status);
"""

from __future__ import annotations

import os
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select

from app.config import carregar_configuracao
from app.domain.entidades import StatusEmprestimo
from app.infra.banco import criar_engine, criar_session_factory
from app.infra.modelos import (
    EmprestimoModelo,
    LivroModelo,
    UsuarioModelo,
    agora_utc,
)

QUANTIDADE_DE_LIVROS = 40
QUANTIDADE_DE_USUARIOS = 200
QUANTIDADE_DE_EMPRESTIMOS = int(os.getenv("VOLUME_EMPRESTIMOS", "20000"))
TAMANHO_DO_LOTE = 2000


def _garantir_livros(banco) -> list:
    livros = list(
        banco.scalars(
            select(LivroModelo).where(
                LivroModelo.isbn.like("volume-%")
            )
        )
    )
    faltam = QUANTIDADE_DE_LIVROS - len(livros)
    for indice in range(max(0, faltam)):
        livro = LivroModelo(
            titulo=f"Livro volume {len(livros) + indice}",
            autor="Seed de volume",
            isbn=f"volume-{len(livros) + indice:04d}",
            exemplares_total=100_000,
            criado_em=agora_utc(),
        )
        banco.add(livro)
        livros.append(livro)
    banco.flush()
    return livros


def _garantir_usuarios(banco) -> list:
    usuarios = list(
        banco.scalars(
            select(UsuarioModelo).where(
                UsuarioModelo.email.like("volume-%@exemplo.com")
            )
        )
    )
    faltam = QUANTIDADE_DE_USUARIOS - len(usuarios)
    for indice in range(max(0, faltam)):
        usuario = UsuarioModelo(
            nome=f"Usuário volume {len(usuarios) + indice}",
            email=f"volume-{len(usuarios) + indice:04d}@exemplo.com",
            criado_em=agora_utc(),
        )
        banco.add(usuario)
        usuarios.append(usuario)
    banco.flush()
    return usuarios


def executar() -> None:
    configuracao = carregar_configuracao()
    motor = criar_engine(configuracao.database_url)
    sessao = criar_session_factory(motor)
    random.seed(42)  # resultado reproduzível

    with sessao() as banco:
        livros = _garantir_livros(banco)
        usuarios = _garantir_usuarios(banco)
        banco.commit()

        print("Apagando empréstimos existentes...")
        banco.execute(delete(EmprestimoModelo))

        base = datetime(2025, 1, 1, tzinfo=UTC).replace(tzinfo=None)
        lote: list[dict] = []
        inseridos = 0

        for indice in range(QUANTIDADE_DE_EMPRESTIMOS):
            data_emprestimo = base + timedelta(
                minutes=random.randint(0, 365 * 24 * 60)
            )
            ativo = random.random() < 0.5
            lote.append(
                {
                    "livro_id": livros[indice % len(livros)].id,
                    "usuario_id": usuarios[indice % len(usuarios)].id,
                    "status": (
                        StatusEmprestimo.ATIVO
                        if ativo
                        else StatusEmprestimo.DEVOLVIDO
                    ),
                    "data_emprestimo": data_emprestimo,
                    "data_prevista": data_emprestimo + timedelta(days=14),
                    "data_devolucao": (
                        None
                        if ativo
                        else data_emprestimo + timedelta(days=7)
                    ),
                }
            )

            if len(lote) == TAMANHO_DO_LOTE:
                banco.execute(insert(EmprestimoModelo), lote)
                inseridos += len(lote)
                lote.clear()

        if lote:
            banco.execute(insert(EmprestimoModelo), lote)
            inseridos += len(lote)

        banco.commit()

    motor.dispose()
    print(f"Seed de volume concluído: {inseridos} empréstimos.")


if __name__ == "__main__":
    executar()
