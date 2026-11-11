"""Testes dos casos de uso de manutenção de cadastros (editar/excluir)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.erros import ErroDeDominio
from app.domain.repositorios import DadosNovoLivro, DadosNovoUsuario
from app.use_cases.atualizar_livro import AtualizarLivro
from app.use_cases.atualizar_usuario import AtualizarUsuario
from app.use_cases.excluir_livro import ExcluirLivro
from app.use_cases.excluir_usuario import ExcluirUsuario
from tests.fakes import (
    LivroRepositorioFake,
    RelogioFake,
    UsuarioRepositorioFake,
    criar_livro_fake,
    criar_usuario_fake,
)

AGORA = datetime(2026, 1, 10, 9)


@pytest.fixture
def repositorios():
    return LivroRepositorioFake(), UsuarioRepositorioFake()


class TestAtualizarLivro:
    def test_edita_titulo_autor_isbn_e_exemplares(self, repositorios):
        livros, _ = repositorios
        livro = criar_livro_fake(3)
        livros.livros.append(livro)

        atualizado = AtualizarLivro(livros).executar(
            livro.id,
            DadosNovoLivro(
                titulo="Título novo",
                autor="Autor novo",
                isbn="9780000000001",
                exemplares_total=5,
            ),
        )

        assert atualizado.id == livro.id
        assert atualizado.titulo == "Título novo"
        assert atualizado.autor == "Autor novo"
        assert atualizado.isbn == "9780000000001"
        assert atualizado.exemplares_total == 5

    def test_recusa_reduzir_exemplares_abaixo_dos_emprestimos_ativos(
        self, repositorios
    ):
        livros, _ = repositorios
        livro = criar_livro_fake(3)
        livros.livros.append(livro)
        livros.emprestimos_ativos = 2

        with pytest.raises(ErroDeDominio) as erro:
            AtualizarLivro(livros).executar(
                livro.id,
                DadosNovoLivro(
                    titulo=livro.titulo,
                    autor=livro.autor,
                    isbn=livro.isbn,
                    exemplares_total=1,
                ),
            )

        assert erro.value.codigo == "EXEMPLARES_ABAIXO_DOS_EMPRESTIMOS"
        assert erro.value.status_code == 409

    def test_retorna_404_quando_o_livro_nao_existe(self, repositorios):
        livros, _ = repositorios

        with pytest.raises(ErroDeDominio) as erro:
            AtualizarLivro(livros).executar(
                uuid4(),
                DadosNovoLivro(
                    titulo="Título",
                    autor="Autor",
                    isbn="9780000000002",
                    exemplares_total=1,
                ),
            )

        assert erro.value.codigo == "LIVRO_NAO_ENCONTRADO"
        assert erro.value.status_code == 404


class TestExcluirLivro:
    def test_exclui_um_livro_sem_emprestimos(self, repositorios):
        livros, _ = repositorios
        livro = criar_livro_fake(1)
        livros.livros.append(livro)

        ExcluirLivro(livros, RelogioFake(AGORA)).executar(livro.id)

        assert livros.buscar_por_id(livro.id) is None
        assert livros.livros == []

    def test_preserva_o_historico_ao_excluir_livro_com_emprestimos(
        self, repositorios
    ):
        livros, _ = repositorios
        livro = criar_livro_fake(1)
        livros.livros.append(livro)
        livros.emprestimos_registrados = 1

        ExcluirLivro(livros, RelogioFake(AGORA)).executar(livro.id)

        # A linha continua no "banco" (histórico), mas sai do catálogo.
        guardado = next(item for item in livros.livros if item.id == livro.id)
        assert guardado.excluido_em == AGORA
        assert livros.buscar_por_id(livro.id) is None
        assert livros.listar_com_disponibilidade() == []

    def test_retorna_404_quando_o_livro_nao_existe(self, repositorios):
        livros, _ = repositorios

        with pytest.raises(ErroDeDominio) as erro:
            ExcluirLivro(livros).executar(uuid4())

        assert erro.value.codigo == "LIVRO_NAO_ENCONTRADO"
        assert erro.value.status_code == 404


class TestAtualizarUsuario:
    def test_edita_nome_e_email(self, repositorios):
        _, usuarios = repositorios
        usuario = criar_usuario_fake()
        usuarios.usuarios.append(usuario)

        atualizado = AtualizarUsuario(usuarios).executar(
            usuario.id,
            DadosNovoUsuario(
                nome="Nome novo", email="nome.novo@exemplo.com"
            ),
        )

        assert atualizado.id == usuario.id
        assert atualizado.nome == "Nome novo"
        assert atualizado.email == "nome.novo@exemplo.com"

    def test_retorna_404_quando_o_usuario_nao_existe(self, repositorios):
        _, usuarios = repositorios

        with pytest.raises(ErroDeDominio) as erro:
            AtualizarUsuario(usuarios).executar(
                uuid4(),
                DadosNovoUsuario(nome="Nome", email="nome@exemplo.com"),
            )

        assert erro.value.codigo == "USUARIO_NAO_ENCONTRADO"
        assert erro.value.status_code == 404


class TestExcluirUsuario:
    def test_exclui_um_usuario_sem_emprestimos(self, repositorios):
        _, usuarios = repositorios
        usuario = criar_usuario_fake()
        usuarios.usuarios.append(usuario)

        ExcluirUsuario(usuarios, RelogioFake(AGORA)).executar(usuario.id)

        assert usuarios.buscar_por_id(usuario.id) is None
        assert usuarios.listar() == []

    def test_preserva_o_historico_ao_excluir_usuario_com_emprestimos(
        self, repositorios
    ):
        _, usuarios = repositorios
        usuario = criar_usuario_fake()
        usuarios.usuarios.append(usuario)
        usuarios.emprestimos_registrados = 1

        ExcluirUsuario(usuarios, RelogioFake(AGORA)).executar(usuario.id)

        guardado = next(
            item for item in usuarios.usuarios if item.id == usuario.id
        )
        assert guardado.excluido_em == AGORA
        assert usuarios.buscar_por_id(usuario.id) is None
        assert usuarios.listar() == []
