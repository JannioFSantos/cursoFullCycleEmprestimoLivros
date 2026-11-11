"""Dublês em memória dos repositórios para os testes unitários.

Eles imitam o comportamento dos repositórios SQLAlchemy, mas sem banco. O
objetivo é testar casos de uso e regras em milissegundos. Quem prova que o SQL
está certo é o teste de integração, em `tests/integration`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entidades import (
    Emprestimo,
    EmprestimoDetalhado,
    Livro,
    LivroComDisponibilidade,
    LivroResumo,
    StatusEmprestimo,
    Usuario,
    UsuarioResumo,
)
from app.domain.erros import erros
from app.domain.regras import (
    EstadoParaAtualizarLivro,
    EstadoParaEmprestar,
    ModoDeExclusao,
    calcular_disponiveis,
    decidir_modo_de_exclusao,
    inicio_do_dia,
)
from app.domain.repositorios import (
    DadosNovoEmprestimo,
    DadosNovoLivro,
    DadosNovoUsuario,
)


class RelogioFake:
    """Relógio que devolve sempre o instante que o teste mandar."""

    def __init__(self, agora: datetime) -> None:
        self.instante = agora

    def agora(self) -> datetime:
        return self.instante


def criar_livro_fake(
    exemplares_total: int = 1,
    **alteracoes,
) -> Livro:
    dados = {
        "id": uuid4(),
        "titulo": "Livro de teste",
        "autor": "Autor de teste",
        "isbn": f"isbn-{uuid4()}",
        "exemplares_total": exemplares_total,
        "criado_em": datetime(2026, 1, 1),
        "excluido_em": None,
    }
    dados.update(alteracoes)
    return Livro(**dados)


def criar_usuario_fake(**alteracoes) -> Usuario:
    dados = {
        "id": uuid4(),
        "nome": "Usuário de teste",
        "email": f"{uuid4()}@exemplo.com",
        "criado_em": datetime(2026, 1, 1),
        "excluido_em": None,
    }
    dados.update(alteracoes)
    return Usuario(**dados)


class LivroRepositorioFake:
    def __init__(self) -> None:
        self.livros: list[Livro] = []
        # Números usados pelos testes de edição/exclusão.
        self.emprestimos_ativos = 0
        self.emprestimos_registrados = 0

    def criar(self, dados: DadosNovoLivro) -> Livro:
        livro = Livro(
            id=uuid4(),
            criado_em=datetime(2026, 1, 1),
            excluido_em=None,
            **vars(dados),
        )
        self.livros.append(livro)
        return livro

    def buscar_por_id(self, id: UUID) -> Livro | None:
        for livro in self.livros:
            if livro.id == id and livro.excluido_em is None:
                return livro
        return None

    def listar_com_disponibilidade(self) -> list[LivroComDisponibilidade]:
        return [
            LivroComDisponibilidade(
                **vars(livro),
                emprestimos_ativos=0,
                exemplares_disponiveis=calcular_disponiveis(
                    livro.exemplares_total, 0
                ),
            )
            for livro in self.livros
            if livro.excluido_em is None
        ]

    def atualizar_com_bloqueio(
        self,
        id: UUID,
        dados: DadosNovoLivro,
        validar: Callable[[EstadoParaAtualizarLivro], None],
    ) -> Livro:
        livro = self.buscar_por_id(id)
        if livro is None:
            raise erros.livro_nao_encontrado()

        validar(
            EstadoParaAtualizarLivro(
                exemplares_total=dados.exemplares_total,
                emprestimos_ativos=self.emprestimos_ativos,
            )
        )

        livro.titulo = dados.titulo
        livro.autor = dados.autor
        livro.isbn = dados.isbn
        livro.exemplares_total = dados.exemplares_total
        return livro

    def excluir(self, id: UUID, quando: datetime) -> None:
        for indice, livro in enumerate(self.livros):
            if livro.id == id and livro.excluido_em is None:
                if (
                    decidir_modo_de_exclusao(self.emprestimos_registrados)
                    == ModoDeExclusao.APAGAR
                ):
                    self.livros.pop(indice)
                    return
                livro.excluido_em = quando
                return

        raise erros.livro_nao_encontrado()


class UsuarioRepositorioFake:
    def __init__(self) -> None:
        self.usuarios: list[Usuario] = []
        self.emprestimos_registrados = 0

    def criar(self, dados: DadosNovoUsuario) -> Usuario:
        usuario = Usuario(
            id=uuid4(),
            criado_em=datetime(2026, 1, 1),
            excluido_em=None,
            **vars(dados),
        )
        self.usuarios.append(usuario)
        return usuario

    def buscar_por_id(self, id: UUID) -> Usuario | None:
        for usuario in self.usuarios:
            if usuario.id == id and usuario.excluido_em is None:
                return usuario
        return None

    def listar(self) -> list[Usuario]:
        return sorted(
            (
                usuario
                for usuario in self.usuarios
                if usuario.excluido_em is None
            ),
            key=lambda usuario: usuario.nome,
        )

    def atualizar(self, id: UUID, dados: DadosNovoUsuario) -> Usuario:
        usuario = self.buscar_por_id(id)
        if usuario is None:
            raise erros.usuario_nao_encontrado()

        usuario.nome = dados.nome
        usuario.email = dados.email
        return usuario

    def excluir(self, id: UUID, quando: datetime) -> None:
        for indice, usuario in enumerate(self.usuarios):
            if usuario.id == id and usuario.excluido_em is None:
                if (
                    decidir_modo_de_exclusao(self.emprestimos_registrados)
                    == ModoDeExclusao.APAGAR
                ):
                    self.usuarios.pop(indice)
                    return
                usuario.excluido_em = quando
                return

        raise erros.usuario_nao_encontrado()


class EmprestimoRepositorioFake:
    def __init__(
        self,
        livros: LivroRepositorioFake,
        usuarios: UsuarioRepositorioFake,
    ) -> None:
        self.livros = livros
        self.usuarios = usuarios
        self.emprestimos: list[Emprestimo] = []

    def criar_com_bloqueio(
        self,
        dados: DadosNovoEmprestimo,
        validar: Callable[[EstadoParaEmprestar], None],
    ) -> Emprestimo:
        livro = self.livros.buscar_por_id(dados.livro_id)
        if livro is None:
            raise erros.livro_nao_encontrado()

        usuario = self.usuarios.buscar_por_id(dados.usuario_id)
        if usuario is None:
            raise erros.usuario_nao_encontrado()

        ativos_do_livro = len(
            [
                emprestimo
                for emprestimo in self.emprestimos
                if emprestimo.livro_id == dados.livro_id
                and emprestimo.status == StatusEmprestimo.ATIVO
            ]
        )
        ativos_do_usuario = len(
            [
                emprestimo
                for emprestimo in self.emprestimos
                if emprestimo.usuario_id == dados.usuario_id
                and emprestimo.status == StatusEmprestimo.ATIVO
            ]
        )

        hoje = inicio_do_dia(dados.data_emprestimo)
        tem_atraso = any(
            emprestimo.usuario_id == dados.usuario_id
            and emprestimo.status == StatusEmprestimo.ATIVO
            and inicio_do_dia(emprestimo.data_prevista) < hoje
            for emprestimo in self.emprestimos
        )

        # Mesma função pura usada em produção.
        validar(
            EstadoParaEmprestar(
                exemplares_total=livro.exemplares_total,
                emprestimos_ativos_do_livro=ativos_do_livro,
                emprestimos_ativos_do_usuario=ativos_do_usuario,
                usuario_tem_atraso=tem_atraso,
            )
        )

        emprestimo = Emprestimo(
            id=uuid4(),
            livro_id=dados.livro_id,
            usuario_id=dados.usuario_id,
            status=StatusEmprestimo.ATIVO,
            data_emprestimo=dados.data_emprestimo,
            data_prevista=dados.data_prevista,
            data_devolucao=None,
        )
        self.emprestimos.append(emprestimo)
        return emprestimo

    def buscar_por_id(self, id: UUID) -> Emprestimo | None:
        for emprestimo in self.emprestimos:
            if emprestimo.id == id:
                return emprestimo
        return None

    def registrar_devolucao(
        self, id: UUID, data_devolucao: datetime
    ) -> Emprestimo:
        emprestimo = self.buscar_por_id(id)
        if emprestimo is None:
            raise erros.emprestimo_nao_encontrado()

        emprestimo.status = StatusEmprestimo.DEVOLVIDO
        emprestimo.data_devolucao = data_devolucao
        return emprestimo

    def listar_atrasados(self, hoje: datetime) -> list[EmprestimoDetalhado]:
        detalhados = []

        for emprestimo in self.emprestimos:
            if emprestimo.status != StatusEmprestimo.ATIVO:
                continue
            if inicio_do_dia(emprestimo.data_prevista) >= inicio_do_dia(hoje):
                continue

            detalhado = self._detalhar(emprestimo)
            if detalhado is not None:
                detalhados.append(detalhado)

        return detalhados

    def listar_detalhados(self) -> list[EmprestimoDetalhado]:
        detalhados = [
            detalhado
            for emprestimo in self.emprestimos
            if (detalhado := self._detalhar(emprestimo)) is not None
        ]
        detalhados.sort(
            key=lambda emprestimo: emprestimo.data_emprestimo, reverse=True
        )
        return detalhados

    def _detalhar(self, emprestimo: Emprestimo):
        # Sem filtrar `excluido_em`: o histórico mostra livro/usuário
        # removidos também.
        livro = next(
            (item for item in self.livros.livros if item.id == emprestimo.livro_id),
            None,
        )
        usuario = next(
            (
                item
                for item in self.usuarios.usuarios
                if item.id == emprestimo.usuario_id
            ),
            None,
        )
        if livro is None or usuario is None:
            return None

        return EmprestimoDetalhado(
            id=emprestimo.id,
            livro_id=emprestimo.livro_id,
            usuario_id=emprestimo.usuario_id,
            status=emprestimo.status,
            data_emprestimo=emprestimo.data_emprestimo,
            data_prevista=emprestimo.data_prevista,
            data_devolucao=emprestimo.data_devolucao,
            livro=LivroResumo(
                id=livro.id,
                titulo=livro.titulo,
                autor=livro.autor,
                excluido_em=livro.excluido_em,
            ),
            usuario=UsuarioResumo(
                id=usuario.id,
                nome=usuario.nome,
                email=usuario.email,
                excluido_em=usuario.excluido_em,
            ),
        )
