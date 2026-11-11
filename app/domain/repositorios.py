"""Portas (Protocols) de acesso a dados.

O domínio e os casos de uso dependem SÓ destes contratos. Quem implementa é a
pasta `app/infra`, com SQLAlchemy. Isso é o padrão Repository e é o que
permite trocar o banco (ou usar um fake nos testes) sem tocar nas regras.

Em outras palavras: o "contrato" mora aqui, a "implementação" mora em infra.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entidades import (
    Emprestimo,
    EmprestimoDetalhado,
    Livro,
    LivroComDisponibilidade,
    Usuario,
)
from app.domain.regras import EstadoParaAtualizarLivro, EstadoParaEmprestar


@dataclass(frozen=True)
class DadosNovoLivro:
    titulo: str
    autor: str
    isbn: str
    exemplares_total: int


@dataclass(frozen=True)
class DadosNovoUsuario:
    nome: str
    email: str


@dataclass(frozen=True)
class DadosNovoEmprestimo:
    livro_id: UUID
    usuario_id: UUID
    data_emprestimo: datetime
    data_prevista: datetime


class LivroRepositorio(Protocol):
    def criar(self, dados: DadosNovoLivro) -> Livro: ...

    def buscar_por_id(self, id: UUID) -> Livro | None: ...

    def listar_com_disponibilidade(self) -> list[LivroComDisponibilidade]: ...

    def atualizar_com_bloqueio(
        self,
        id: UUID,
        dados: DadosNovoLivro,
        validar: Callable[[EstadoParaAtualizarLivro], None],
    ) -> Livro:
        """Atualiza o livro com a linha travada (FOR UPDATE)."""
        ...

    def excluir(self, id: UUID, quando: datetime) -> None:
        """Exclui o livro (ou só marca `excluido_em` se houver histórico)."""
        ...


class UsuarioRepositorio(Protocol):
    def criar(self, dados: DadosNovoUsuario) -> Usuario: ...

    def buscar_por_id(self, id: UUID) -> Usuario | None: ...

    def listar(self) -> list[Usuario]:
        """Lista todos os usuários em ordem alfabética."""
        ...

    def atualizar(self, id: UUID, dados: DadosNovoUsuario) -> Usuario: ...

    def excluir(self, id: UUID, quando: datetime) -> None:
        """Exclui o usuário (ou só marca `excluido_em` se houver histórico)."""
        ...


class EmprestimoRepositorio(Protocol):
    def criar_com_bloqueio(
        self,
        dados: DadosNovoEmprestimo,
        validar: Callable[[EstadoParaEmprestar], None],
    ) -> Emprestimo:
        """Cria o empréstimo de forma atômica, validando dentro da transação."""
        ...

    def buscar_por_id(self, id: UUID) -> Emprestimo | None: ...

    def registrar_devolucao(
        self, id: UUID, data_devolucao: datetime
    ) -> Emprestimo: ...

    def listar_atrasados(self, hoje: datetime) -> list[EmprestimoDetalhado]: ...

    def listar_detalhados(self) -> list[EmprestimoDetalhado]:
        """Lista todos os empréstimos, do mais recente para o mais antigo."""
        ...
