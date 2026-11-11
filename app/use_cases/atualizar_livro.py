"""Caso de uso: editar um livro.

A regra importante é não deixar a quantidade de exemplares ficar menor do que
o número de empréstimos ativos. Quem garante que a contagem e a gravação
acontecem juntas é o repositório (transação com FOR UPDATE).
"""

from __future__ import annotations

from uuid import UUID

from app.domain.entidades import Livro
from app.domain.regras import validar_atualizacao_de_livro
from app.domain.repositorios import DadosNovoLivro, LivroRepositorio


class AtualizarLivro:
    def __init__(self, livros: LivroRepositorio) -> None:
        self._livros = livros

    def executar(self, id: UUID, dados: DadosNovoLivro) -> Livro:
        return self._livros.atualizar_com_bloqueio(
            id, dados, validar_atualizacao_de_livro
        )
