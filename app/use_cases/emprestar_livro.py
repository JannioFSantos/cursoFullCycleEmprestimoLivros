"""Caso de uso: emprestar um livro.

Um caso de uso orquestra repositórios, aplica as regras do domínio e devolve o
resultado. Ele não sabe nada de HTTP (status code, JSON) nem de SQL. Essa
separação é o S do SOLID (Single Responsibility) na prática.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entidades import Emprestimo
from app.domain.erros import erros
from app.domain.regras import (
    LIMITE_PADRAO_DE_EMPRESTIMOS,
    PRAZO_PADRAO_EM_DIAS,
    calcular_data_prevista,
    validar_emprestimo,
)
from app.domain.relogio import Relogio, relogio_do_sistema
from app.domain.repositorios import (
    EmprestimoRepositorio,
    LivroRepositorio,
    UsuarioRepositorio,
)


@dataclass(frozen=True)
class EntradaEmprestarLivro:
    livro_id: UUID
    usuario_id: UUID


class EmprestarLivro:
    def __init__(
        self,
        livros: LivroRepositorio,
        usuarios: UsuarioRepositorio,
        emprestimos: EmprestimoRepositorio,
        relogio: Relogio = relogio_do_sistema,
        prazo_em_dias: int = PRAZO_PADRAO_EM_DIAS,
        limite_de_emprestimos: int = LIMITE_PADRAO_DE_EMPRESTIMOS,
    ) -> None:
        self._livros = livros
        self._usuarios = usuarios
        self._emprestimos = emprestimos
        self._relogio = relogio
        self._prazo_em_dias = prazo_em_dias
        self._limite_de_emprestimos = limite_de_emprestimos

    def executar(self, entrada: EntradaEmprestarLivro) -> Emprestimo:
        # 1) Verificações de existência -> erro 404 com mensagem clara.
        livro = self._livros.buscar_por_id(entrada.livro_id)
        if livro is None:
            raise erros.livro_nao_encontrado()

        usuario = self._usuarios.buscar_por_id(entrada.usuario_id)
        if usuario is None:
            raise erros.usuario_nao_encontrado()

        # 2) Calculamos as datas a partir do MESMO instante para não haver
        #    diferença de microssegundos entre empréstimo e vencimento.
        agora = self._relogio.agora()
        data_prevista = calcular_data_prevista(agora, self._prazo_em_dias)

        # 3) O repositório abre transação, bloqueia o livro e só grava depois
        #    de chamar `validar_emprestimo` com o estado real do banco.
        return self._emprestimos.criar_com_bloqueio(
            dados=_dados(entrada.livro_id, entrada.usuario_id, agora, data_prevista),
            validar=lambda estado: validar_emprestimo(
                estado, self._limite_de_emprestimos
            ),
        )


def _dados(livro_id: UUID, usuario_id: UUID, agora, data_prevista):
    from app.domain.repositorios import DadosNovoEmprestimo

    return DadosNovoEmprestimo(
        livro_id=livro_id,
        usuario_id=usuario_id,
        data_emprestimo=agora,
        data_prevista=data_prevista,
    )
