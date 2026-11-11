"""Dependências compartilhadas pelas rotas HTTP e pela tela de demonstração."""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import CollectorRegistry
from sqlalchemy import Engine

from app.domain.relogio import Relogio
from app.domain.repositorios import (
    EmprestimoRepositorio,
    LivroRepositorio,
    UsuarioRepositorio,
)
from app.observabilidade.metricas import Metricas
from app.use_cases.atualizar_livro import AtualizarLivro
from app.use_cases.atualizar_usuario import AtualizarUsuario
from app.use_cases.devolver_emprestimo import DevolverEmprestimo
from app.use_cases.emprestar_livro import EmprestarLivro
from app.use_cases.excluir_livro import ExcluirLivro
from app.use_cases.excluir_usuario import ExcluirUsuario


@dataclass(frozen=True)
class Dependencias:
    engine: Engine
    livros: LivroRepositorio
    usuarios: UsuarioRepositorio
    emprestimos: EmprestimoRepositorio
    emprestar_livro: EmprestarLivro
    devolver_emprestimo: DevolverEmprestimo
    atualizar_livro: AtualizarLivro
    excluir_livro: ExcluirLivro
    atualizar_usuario: AtualizarUsuario
    excluir_usuario: ExcluirUsuario
    relogio: Relogio
    metricas: Metricas
    registro: CollectorRegistry
