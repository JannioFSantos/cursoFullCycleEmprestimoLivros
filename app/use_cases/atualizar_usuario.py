"""Caso de uso: editar um usuário.

Verificamos se ele existe antes de atualizar para devolver 404 no formato
padrão, em vez de deixar o banco estourar um erro interno. E-mail repetido
continua sendo barrado pelo índice único do banco (409 VALOR_JA_CADASTRADO).
"""

from __future__ import annotations

from uuid import UUID

from app.domain.entidades import Usuario
from app.domain.erros import erros
from app.domain.repositorios import DadosNovoUsuario, UsuarioRepositorio


class AtualizarUsuario:
    def __init__(self, usuarios: UsuarioRepositorio) -> None:
        self._usuarios = usuarios

    def executar(self, id: UUID, dados: DadosNovoUsuario) -> Usuario:
        usuario = self._usuarios.buscar_por_id(id)
        if usuario is None:
            raise erros.usuario_nao_encontrado()

        return self._usuarios.atualizar(id, dados)
