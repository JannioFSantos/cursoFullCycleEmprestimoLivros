"""Testes do caso de uso "devolver empréstimo"."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.erros import ErroDeDominio
from app.use_cases.devolver_emprestimo import DevolverEmprestimo
from app.use_cases.emprestar_livro import EmprestarLivro, EntradaEmprestarLivro
from tests.fakes import (
    EmprestimoRepositorioFake,
    LivroRepositorioFake,
    RelogioFake,
    UsuarioRepositorioFake,
    criar_livro_fake,
    criar_usuario_fake,
)

AGORA = datetime(2026, 1, 10, 9)


@pytest.fixture
def cenario():
    livros = LivroRepositorioFake()
    usuarios = UsuarioRepositorioFake()
    emprestimos = EmprestimoRepositorioFake(livros, usuarios)
    return livros, usuarios, emprestimos


def criar_emprestimo(livros, usuarios, emprestimos):
    livro = criar_livro_fake(1)
    usuario = criar_usuario_fake()
    livros.livros.append(livro)
    usuarios.usuarios.append(usuario)

    emprestar = EmprestarLivro(
        livros,
        usuarios,
        emprestimos,
        RelogioFake(datetime(2026, 1, 5, 12)),
        14,
        3,
    )
    return emprestar.executar(
        EntradaEmprestarLivro(livro_id=livro.id, usuario_id=usuario.id)
    )


def test_marca_o_emprestimo_como_devolvido_com_a_data_atual(cenario):
    livros, usuarios, emprestimos = cenario
    emprestimo = criar_emprestimo(livros, usuarios, emprestimos)
    devolver = DevolverEmprestimo(emprestimos, RelogioFake(AGORA))

    devolvido = devolver.executar(emprestimo.id)

    assert devolvido.status.value == "DEVOLVIDO"
    assert devolvido.data_devolucao == AGORA


def test_retorna_404_quando_o_emprestimo_nao_existe(cenario):
    from uuid import uuid4

    _, _, emprestimos = cenario
    devolver = DevolverEmprestimo(emprestimos)

    with pytest.raises(ErroDeDominio) as erro:
        devolver.executar(uuid4())

    assert erro.value.codigo == "EMPRESTIMO_NAO_ENCONTRADO"
    assert erro.value.status_code == 404


def test_recusa_devolver_o_mesmo_emprestimo_duas_vezes(cenario):
    livros, usuarios, emprestimos = cenario
    emprestimo = criar_emprestimo(livros, usuarios, emprestimos)
    devolver = DevolverEmprestimo(emprestimos, RelogioFake(AGORA))

    devolver.executar(emprestimo.id)

    with pytest.raises(ErroDeDominio) as erro:
        devolver.executar(emprestimo.id)

    assert erro.value.codigo == "EMPRESTIMO_JA_DEVOLVIDO"
    assert erro.value.status_code == 409
