"""Caso de uso: excluir um livro.

A regra de "apagar de verdade ou só marcar como excluído" está no domínio
(`decidir_modo_de_exclusao`) e é aplicada pelo repositório dentro de uma
transação. Livro com empréstimos sai do catálogo, mas o histórico continua
aparecendo na lista de empréstimos.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.relogio import Relogio, relogio_do_sistema
from app.domain.repositorios import LivroRepositorio


class ExcluirLivro:
    def __init__(
        self,
        livros: LivroRepositorio,
        relogio: Relogio = relogio_do_sistema,
    ) -> None:
        self._livros = livros
        self._relogio = relogio

    def executar(self, id: UUID) -> None:
        self._livros.excluir(id, self._relogio.agora())
