"""Testes do caso de uso "emprestar livro".

Os três repositórios são fakes em memória. O que provamos aqui é a orquestração:
buscar livro/usuário, calcular datas, delegar a validação e devolver o
empréstimo criado — inclusive nos caminhos de erro.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.erros import ErroDeDominio
from app.use_cases.emprestar_livro import EmprestarLivro, EntradaEmprestarLivro
from tests.fakes import (
    EmprestimoRepositorioFake,
    LivroRepositorioFake,
    RelogioFake,
    UsuarioRepositorioFake,
    criar_livro_fake,
    criar_usuario_fake,
)

AGORA = datetime(2026, 1, 5, 12)


@pytest.fixture
def cenario():
    livros = LivroRepositorioFake()
    usuarios = UsuarioRepositorioFake()
    emprestimos = EmprestimoRepositorioFake(livros, usuarios)
    caso_de_uso = EmprestarLivro(
        livros,
        usuarios,
        emprestimos,
        RelogioFake(AGORA),
        14,
        3,
    )
    return livros, usuarios, emprestimos, caso_de_uso


def preparar(livros, usuarios, exemplares_total: int = 1):
    livro = criar_livro_fake(exemplares_total)
    usuario = criar_usuario_fake()
    livros.livros.append(livro)
    usuarios.usuarios.append(usuario)
    return livro, usuario


def test_cria_o_emprestimo_com_prazo_de_14_dias(cenario):
    livros, usuarios, emprestimos, caso_de_uso = cenario
    livro, usuario = preparar(livros, usuarios)

    emprestimo = caso_de_uso.executar(
        EntradaEmprestarLivro(livro_id=livro.id, usuario_id=usuario.id)
    )

    assert emprestimo.status.value == "ATIVO"
    assert emprestimo.data_emprestimo == AGORA
    assert emprestimo.data_prevista == datetime(2026, 1, 19)
    assert len(emprestimos.emprestimos) == 1


def test_retorna_404_quando_o_livro_nao_existe(cenario):
    _, usuarios, _, caso_de_uso = cenario
    usuario = criar_usuario_fake()
    usuarios.usuarios.append(usuario)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(livro_id=uuid4(), usuario_id=usuario.id)
        )

    assert erro.value.codigo == "LIVRO_NAO_ENCONTRADO"
    assert erro.value.status_code == 404


def test_retorna_404_quando_o_usuario_nao_existe(cenario):
    livros, usuarios, _, caso_de_uso = cenario
    livro, _ = preparar(livros, usuarios)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(livro_id=livro.id, usuario_id=uuid4())
        )

    assert erro.value.codigo == "USUARIO_NAO_ENCONTRADO"
    assert erro.value.status_code == 404


def test_recusa_quando_nao_ha_exemplar_disponivel(cenario):
    livros, usuarios, _, caso_de_uso = cenario
    livro, usuario = preparar(livros, usuarios, 1)

    caso_de_uso.executar(
        EntradaEmprestarLivro(livro_id=livro.id, usuario_id=usuario.id)
    )

    outro_usuario = criar_usuario_fake()
    usuarios.usuarios.append(outro_usuario)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(
                livro_id=livro.id, usuario_id=outro_usuario.id
            )
        )

    assert erro.value.codigo == "LIVRO_INDISPONIVEL"


def test_recusa_usuario_com_emprestimo_em_atraso(cenario):
    livros, usuarios, emprestimos, caso_de_uso = cenario

    no_passado = EmprestarLivro(
        livros,
        usuarios,
        emprestimos,
        RelogioFake(datetime(2025, 12, 1, 12)),
        14,
        3,
    )

    livro_antigo = criar_livro_fake(1)
    livros.livros.append(livro_antigo)
    usuario = criar_usuario_fake()
    usuarios.usuarios.append(usuario)

    no_passado.executar(
        EntradaEmprestarLivro(livro_id=livro_antigo.id, usuario_id=usuario.id)
    )

    livro_novo = criar_livro_fake(1)
    livros.livros.append(livro_novo)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(livro_id=livro_novo.id, usuario_id=usuario.id)
        )

    assert erro.value.codigo == "USUARIO_COM_ATRASO"


def test_recusa_ao_atingir_3_emprestimos_ativos(cenario):
    livros, usuarios, _, caso_de_uso = cenario
    usuario = criar_usuario_fake()
    usuarios.usuarios.append(usuario)

    for _ in range(3):
        livro = criar_livro_fake(1)
        livros.livros.append(livro)
        caso_de_uso.executar(
            EntradaEmprestarLivro(livro_id=livro.id, usuario_id=usuario.id)
        )

    quarto_livro = criar_livro_fake(1)
    livros.livros.append(quarto_livro)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(
                livro_id=quarto_livro.id, usuario_id=usuario.id
            )
        )

    assert erro.value.codigo == "LIMITE_ATINGIDO"


def test_o_erro_de_negocio_carrega_mensagem_pronta_para_a_api(cenario):
    livros, usuarios, _, caso_de_uso = cenario
    livro, usuario = preparar(livros, usuarios, 1)
    caso_de_uso.executar(
        EntradaEmprestarLivro(livro_id=livro.id, usuario_id=usuario.id)
    )

    outro_usuario = criar_usuario_fake()
    usuarios.usuarios.append(outro_usuario)

    with pytest.raises(ErroDeDominio) as erro:
        caso_de_uso.executar(
            EntradaEmprestarLivro(
                livro_id=livro.id, usuario_id=outro_usuario.id
            )
        )

    assert erro.value.status_code == 409
    assert "exemplar" in str(erro.value)
