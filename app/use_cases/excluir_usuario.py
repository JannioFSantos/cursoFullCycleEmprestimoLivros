"""Caso de uso: excluir um usuário.

Mesma proteção do livro: se já existe empréstimo, o usuário não é apagado do
banco. Ele só sai da lista, e o histórico continua mostrando quem pegou cada
livro.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.relogio import Relogio, relogio_do_sistema
from app.domain.repositorios import UsuarioRepositorio


class ExcluirUsuario:
    def __init__(
        self,
        usuarios: UsuarioRepositorio,
        relogio: Relogio = relogio_do_sistema,
    ) -> None:
        self._usuarios = usuarios
        self._relogio = relogio

    def executar(self, id: UUID) -> None:
        self._usuarios.excluir(id, self._relogio.agora())
