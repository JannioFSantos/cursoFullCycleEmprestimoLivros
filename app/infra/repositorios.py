"""Implementações dos repositórios com SQLAlchemy.

Estes arquivos só traduzem operações de banco. Nenhuma regra de negócio mora
aqui: se você sentir vontade de escrever um `if` de negócio neste arquivo,
provavelmente ele pertence ao domínio.

O arquivo mais delicado é o de empréstimos, porque é onde garantimos que dois
pedidos simultâneos não levem o mesmo último exemplar. Leia o ADR 0001 antes
de mexer aqui.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, joinedload, sessionmaker

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
from app.infra.modelos import (
    EmprestimoModelo,
    LivroModelo,
    UsuarioModelo,
    agora_utc,
)

# ---------------------------------------------------------------------------
# Conversão modelo -> entidade
# ---------------------------------------------------------------------------


def _para_livro(modelo: LivroModelo) -> Livro:
    return Livro(
        id=modelo.id,
        titulo=modelo.titulo,
        autor=modelo.autor,
        isbn=modelo.isbn,
        exemplares_total=modelo.exemplares_total,
        criado_em=modelo.criado_em,
        excluido_em=modelo.excluido_em,
    )


def _para_usuario(modelo: UsuarioModelo) -> Usuario:
    return Usuario(
        id=modelo.id,
        nome=modelo.nome,
        email=modelo.email,
        criado_em=modelo.criado_em,
        excluido_em=modelo.excluido_em,
    )


def _para_emprestimo(modelo: EmprestimoModelo) -> Emprestimo:
    return Emprestimo(
        id=modelo.id,
        livro_id=modelo.livro_id,
        usuario_id=modelo.usuario_id,
        status=modelo.status,
        data_emprestimo=modelo.data_emprestimo,
        data_prevista=modelo.data_prevista,
        data_devolucao=modelo.data_devolucao,
    )


def _para_emprestimo_detalhado(modelo: EmprestimoModelo) -> EmprestimoDetalhado:
    return EmprestimoDetalhado(
        id=modelo.id,
        livro_id=modelo.livro_id,
        usuario_id=modelo.usuario_id,
        status=modelo.status,
        data_emprestimo=modelo.data_emprestimo,
        data_prevista=modelo.data_prevista,
        data_devolucao=modelo.data_devolucao,
        livro=LivroResumo(
            id=modelo.livro.id,
            titulo=modelo.livro.titulo,
            autor=modelo.livro.autor,
            excluido_em=modelo.livro.excluido_em,
        ),
        usuario=UsuarioResumo(
            id=modelo.usuario.id,
            nome=modelo.usuario.nome,
            email=modelo.usuario.email,
            excluido_em=modelo.usuario.excluido_em,
        ),
    )


# ---------------------------------------------------------------------------
# Livros
# ---------------------------------------------------------------------------


class SqlAlchemyLivroRepositorio:
    def __init__(self, sessao: sessionmaker[Session]) -> None:
        self._sessao = sessao

    def criar(self, dados: DadosNovoLivro) -> Livro:
        with self._sessao() as sessao:
            modelo = LivroModelo(
                titulo=dados.titulo,
                autor=dados.autor,
                isbn=dados.isbn,
                exemplares_total=dados.exemplares_total,
                criado_em=agora_utc(),
            )
            sessao.add(modelo)
            sessao.commit()
            sessao.refresh(modelo)
            return _para_livro(modelo)

    def buscar_por_id(self, id: UUID) -> Livro | None:
        """Livro marcado como excluído não conta mais como "encontrado"."""
        with self._sessao() as sessao:
            modelo = sessao.execute(
                select(LivroModelo).where(
                    LivroModelo.id == id,
                    LivroModelo.excluido_em.is_(None),
                )
            ).scalar_one_or_none()
            return _para_livro(modelo) if modelo else None

    def listar_com_disponibilidade(self) -> list[LivroComDisponibilidade]:
        """Lista os livros já com a contagem de empréstimos ativos.

        A subconsulta conta apenas os ATIVOS direto no PostgreSQL, em vez de
        carregar todos os empréstimos para a memória.
        """
        ativos = (
            select(
                EmprestimoModelo.livro_id,
                func.count().label("total"),
            )
            .where(EmprestimoModelo.status == StatusEmprestimo.ATIVO)
            .group_by(EmprestimoModelo.livro_id)
            .subquery()
        )

        consulta = (
            select(LivroModelo, func.coalesce(ativos.c.total, 0))
            .outerjoin(ativos, ativos.c.livro_id == LivroModelo.id)
            # Livros excluídos continuam no banco por causa do histórico, mas
            # não aparecem no catálogo.
            .where(LivroModelo.excluido_em.is_(None))
            .order_by(LivroModelo.titulo)
        )

        with self._sessao() as sessao:
            linhas = sessao.execute(consulta).all()

        return [
            LivroComDisponibilidade(
                id=livro.id,
                titulo=livro.titulo,
                autor=livro.autor,
                isbn=livro.isbn,
                exemplares_total=livro.exemplares_total,
                criado_em=livro.criado_em,
                excluido_em=livro.excluido_em,
                emprestimos_ativos=int(quantidade),
                exemplares_disponiveis=calcular_disponiveis(
                    livro.exemplares_total, int(quantidade)
                ),
            )
            for livro, quantidade in linhas
        ]

    def atualizar_com_bloqueio(
        self,
        id: UUID,
        dados: DadosNovoLivro,
        validar: Callable[[EstadoParaAtualizarLivro], None],
    ) -> Livro:
        """Atualiza o livro dentro de uma transação com FOR UPDATE.

        O lock impede que um empréstimo novo entre entre a contagem e o update,
        deixando `exemplares_total` menor que os empréstimos ativos.
        """
        with self._sessao() as sessao, sessao.begin():
            modelo = self._travar_livro(sessao, id)

            emprestimos_ativos = int(
                sessao.scalar(
                    select(func.count())
                    .select_from(EmprestimoModelo)
                    .where(
                        EmprestimoModelo.livro_id == id,
                        EmprestimoModelo.status == StatusEmprestimo.ATIVO,
                    )
                )
                or 0
            )

            # A regra é pura e mora no domínio; aqui só passamos o estado atual.
            validar(
                EstadoParaAtualizarLivro(
                    exemplares_total=dados.exemplares_total,
                    emprestimos_ativos=emprestimos_ativos,
                )
            )

            modelo.titulo = dados.titulo
            modelo.autor = dados.autor
            modelo.isbn = dados.isbn
            modelo.exemplares_total = dados.exemplares_total
            sessao.flush()
            return _para_livro(modelo)

    def excluir(self, id: UUID, quando: datetime) -> None:
        """Exclui o livro com a linha travada.

        Se ele nunca teve empréstimo, apaga de verdade.
        Se já teve, NÃO apaga: grava `excluido_em`. A decisão vem do domínio.
        """
        with self._sessao() as sessao, sessao.begin():
            modelo = self._travar_livro(sessao, id)

            emprestimos_registrados = int(
                sessao.scalar(
                    select(func.count())
                    .select_from(EmprestimoModelo)
                    .where(EmprestimoModelo.livro_id == id)
                )
                or 0
            )

            if (
                decidir_modo_de_exclusao(emprestimos_registrados)
                == ModoDeExclusao.APAGAR
            ):
                sessao.delete(modelo)
                return

            modelo.excluido_em = quando

    @staticmethod
    def _travar_livro(sessao: Session, id: UUID) -> LivroModelo:
        modelo = sessao.execute(
            select(LivroModelo)
            .where(
                LivroModelo.id == id,
                LivroModelo.excluido_em.is_(None),
            )
            .with_for_update()
        ).scalar_one_or_none()

        if modelo is None:
            raise erros.livro_nao_encontrado()
        return modelo


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------


class SqlAlchemyUsuarioRepositorio:
    def __init__(self, sessao: sessionmaker[Session]) -> None:
        self._sessao = sessao

    def criar(self, dados: DadosNovoUsuario) -> Usuario:
        with self._sessao() as sessao:
            modelo = UsuarioModelo(
                nome=dados.nome,
                email=dados.email,
                criado_em=agora_utc(),
            )
            sessao.add(modelo)
            sessao.commit()
            sessao.refresh(modelo)
            return _para_usuario(modelo)

    def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Usuário marcado como excluído não é mais encontrado."""
        with self._sessao() as sessao:
            modelo = sessao.execute(
                select(UsuarioModelo).where(
                    UsuarioModelo.id == id,
                    UsuarioModelo.excluido_em.is_(None),
                )
            ).scalar_one_or_none()
            return _para_usuario(modelo) if modelo else None

    def listar(self) -> list[Usuario]:
        with self._sessao() as sessao:
            modelos = (
                sessao.execute(
                    select(UsuarioModelo)
                    .where(UsuarioModelo.excluido_em.is_(None))
                    .order_by(UsuarioModelo.nome)
                )
                .scalars()
                .all()
            )
            return [_para_usuario(modelo) for modelo in modelos]

    def atualizar(self, id: UUID, dados: DadosNovoUsuario) -> Usuario:
        with self._sessao() as sessao, sessao.begin():
            # O filtro `excluido_em IS NULL` evita editar um usuário que acabou
            # de ser excluído por outra requisição.
            resultado = sessao.execute(
                update(UsuarioModelo)
                .where(
                    UsuarioModelo.id == id,
                    UsuarioModelo.excluido_em.is_(None),
                )
                .values(nome=dados.nome, email=dados.email)
            )

            if resultado.rowcount == 0:
                raise erros.usuario_nao_encontrado()

            modelo = sessao.get(UsuarioModelo, id)
            if modelo is None:  # pragma: no cover - corrida improvável
                raise erros.usuario_nao_encontrado()
            return _para_usuario(modelo)

    def excluir(self, id: UUID, quando: datetime) -> None:
        with self._sessao() as sessao, sessao.begin():
            modelo = sessao.execute(
                select(UsuarioModelo)
                .where(
                    UsuarioModelo.id == id,
                    UsuarioModelo.excluido_em.is_(None),
                )
                .with_for_update()
            ).scalar_one_or_none()

            if modelo is None:
                raise erros.usuario_nao_encontrado()

            emprestimos_registrados = int(
                sessao.scalar(
                    select(func.count())
                    .select_from(EmprestimoModelo)
                    .where(EmprestimoModelo.usuario_id == id)
                )
                or 0
            )

            if (
                decidir_modo_de_exclusao(emprestimos_registrados)
                == ModoDeExclusao.APAGAR
            ):
                sessao.delete(modelo)
                return

            modelo.excluido_em = quando


# ---------------------------------------------------------------------------
# Empréstimos
# ---------------------------------------------------------------------------


class SqlAlchemyEmprestimoRepositorio:
    def __init__(self, sessao: sessionmaker[Session]) -> None:
        self._sessao = sessao

    def criar_com_bloqueio(
        self,
        dados: DadosNovoEmprestimo,
        validar: Callable[[EstadoParaEmprestar], None],
    ) -> Emprestimo:
        """Cria o empréstimo de forma atômica.

        A transação inteira confirma ou é desfeita. A ordem dos locks é sempre
        livro -> usuário, para evitar deadlock.
        """
        with self._sessao() as sessao, sessao.begin():
            # Equivalente ao timeout de 10s do Prisma: em caso de espera longa
            # por lock, o PostgreSQL aborta e a API responde 500 (erro real).
            sessao.execute(text("SET LOCAL lock_timeout = '10s'"))

            livro = sessao.execute(
                select(LivroModelo)
                .where(
                    LivroModelo.id == dados.livro_id,
                    LivroModelo.excluido_em.is_(None),
                )
                .with_for_update()
            ).scalar_one_or_none()

            if livro is None:
                raise erros.livro_nao_encontrado()

            usuario = sessao.execute(
                select(UsuarioModelo)
                .where(
                    UsuarioModelo.id == dados.usuario_id,
                    UsuarioModelo.excluido_em.is_(None),
                )
                .with_for_update()
            ).scalar_one_or_none()

            if usuario is None:
                raise erros.usuario_nao_encontrado()

            emprestimos_ativos_do_livro = int(
                sessao.scalar(
                    select(func.count())
                    .select_from(EmprestimoModelo)
                    .where(
                        EmprestimoModelo.livro_id == dados.livro_id,
                        EmprestimoModelo.status == StatusEmprestimo.ATIVO,
                    )
                )
                or 0
            )

            emprestimos_ativos_do_usuario = int(
                sessao.scalar(
                    select(func.count())
                    .select_from(EmprestimoModelo)
                    .where(
                        EmprestimoModelo.usuario_id == dados.usuario_id,
                        EmprestimoModelo.status == StatusEmprestimo.ATIVO,
                    )
                )
                or 0
            )

            emprestimo_em_atraso = sessao.scalar(
                select(EmprestimoModelo.id)
                .where(
                    EmprestimoModelo.usuario_id == dados.usuario_id,
                    EmprestimoModelo.status == StatusEmprestimo.ATIVO,
                    EmprestimoModelo.data_prevista
                    < inicio_do_dia(dados.data_emprestimo),
                )
                .limit(1)
            )

            # A regra de negócio é a MESMA função pura testada nos unitários.
            # Se ela lançar erro, a transação é desfeita automaticamente.
            validar(
                EstadoParaEmprestar(
                    exemplares_total=livro.exemplares_total,
                    emprestimos_ativos_do_livro=emprestimos_ativos_do_livro,
                    emprestimos_ativos_do_usuario=emprestimos_ativos_do_usuario,
                    usuario_tem_atraso=emprestimo_em_atraso is not None,
                )
            )

            modelo = EmprestimoModelo(
                livro_id=dados.livro_id,
                usuario_id=dados.usuario_id,
                status=StatusEmprestimo.ATIVO,
                data_emprestimo=dados.data_emprestimo,
                data_prevista=dados.data_prevista,
            )
            sessao.add(modelo)
            sessao.flush()
            return _para_emprestimo(modelo)

    def buscar_por_id(self, id: UUID) -> Emprestimo | None:
        with self._sessao() as sessao:
            modelo = sessao.get(EmprestimoModelo, id)
            return _para_emprestimo(modelo) if modelo else None

    def registrar_devolucao(
        self, id: UUID, data_devolucao: datetime
    ) -> Emprestimo:
        with self._sessao() as sessao, sessao.begin():
            modelo = sessao.get(EmprestimoModelo, id)
            if modelo is None:
                raise erros.emprestimo_nao_encontrado()

            modelo.status = StatusEmprestimo.DEVOLVIDO
            modelo.data_devolucao = data_devolucao
            sessao.flush()
            return _para_emprestimo(modelo)

    def listar_atrasados(self, hoje: datetime) -> list[EmprestimoDetalhado]:
        """Ativos com data prevista anterior a hoje, do mais antigo ao mais novo."""
        with self._sessao() as sessao:
            modelos = (
                sessao.execute(
                    select(EmprestimoModelo)
                    .where(
                        EmprestimoModelo.status == StatusEmprestimo.ATIVO,
                        EmprestimoModelo.data_prevista < inicio_do_dia(hoje),
                    )
                    .order_by(EmprestimoModelo.data_prevista)
                    .options(
                        joinedload(EmprestimoModelo.livro),
                        joinedload(EmprestimoModelo.usuario),
                    )
                )
                .unique()
                .scalars()
                .all()
            )
            return [_para_emprestimo_detalhado(modelo) for modelo in modelos]

    def listar_detalhados(self) -> list[EmprestimoDetalhado]:
        """Todos os empréstimos, com livro e usuário, do mais recente ao antigo.

        Livro/usuário excluídos continuam aparecendo aqui: é exatamente o
        histórico que a exclusão lógica preserva.
        """
        with self._sessao() as sessao:
            modelos = (
                sessao.execute(
                    select(EmprestimoModelo)
                    .order_by(EmprestimoModelo.data_emprestimo.desc())
                    .options(
                        joinedload(EmprestimoModelo.livro),
                        joinedload(EmprestimoModelo.usuario),
                    )
                )
                .unique()
                .scalars()
                .all()
            )
            return [_para_emprestimo_detalhado(modelo) for modelo in modelos]
