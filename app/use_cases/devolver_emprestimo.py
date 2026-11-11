"""Caso de uso: registrar a devolução de um empréstimo.

Duas regras:
 1. o empréstimo precisa existir (404 se não existir);
 2. não pode ser devolvido duas vezes (409).

A data da devolução vem do relógio injetado, nunca de `datetime.now()` direto.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.entidades import Emprestimo, StatusEmprestimo
from app.domain.erros import erros
from app.domain.relogio import Relogio, relogio_do_sistema
from app.domain.repositorios import EmprestimoRepositorio


class DevolverEmprestimo:
    def __init__(
        self,
        emprestimos: EmprestimoRepositorio,
        relogio: Relogio = relogio_do_sistema,
    ) -> None:
        self._emprestimos = emprestimos
        self._relogio = relogio

    def executar(self, emprestimo_id: UUID) -> Emprestimo:
        emprestimo = self._emprestimos.buscar_por_id(emprestimo_id)
        if emprestimo is None:
            raise erros.emprestimo_nao_encontrado()

        # Devolver de novo não é erro do cliente? É conflito de estado, 409.
        if emprestimo.status == StatusEmprestimo.DEVOLVIDO:
            raise erros.emprestimo_ja_devolvido()

        return self._emprestimos.registrar_devolucao(
            emprestimo_id, self._relogio.agora()
        )
