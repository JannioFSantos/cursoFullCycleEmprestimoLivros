"""Regras de negócio puras da biblioteca.

"Pura" significa: recebe dados, devolve dados (ou lança erro) e não acessa
banco, rede, relógio do sistema nem variável global. Isso torna cada regra
trivial de testar e de explicar em uma apresentação.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.entidades import Emprestimo, StatusEmprestimo
from app.domain.erros import erros

# Prazo padrão de devolução, em dias. Pode ser sobrescrito por PRAZO_DIAS.
PRAZO_PADRAO_EM_DIAS = 14

# Quantos empréstimos simultâneos um usuário pode ter.
LIMITE_PADRAO_DE_EMPRESTIMOS = 3


def inicio_do_dia(data: datetime) -> datetime:
    """Zera horas/minutos/segundos (UTC).

    Trabalhamos com datas "de calendário": um livro que vence hoje ainda NÃO
    está atrasado, independentemente do horário em que foi emprestado. Fazer
    essa conta em UTC evita bug de fuso horário no servidor.
    """
    return data.replace(hour=0, minute=0, second=0, microsecond=0)


def calcular_data_prevista(data_emprestimo: datetime, prazo_em_dias: int) -> datetime:
    """Calcula a data de devolução: dia do empréstimo + prazo, à meia-noite UTC.

    Ex.: emprestado em 05/01 com prazo de 14 dias -> previsto para 19/01 00:00.
    """
    return inicio_do_dia(data_emprestimo) + timedelta(days=prazo_em_dias)


def calcular_disponiveis(exemplares_total: int, emprestimos_ativos: int) -> int:
    """Disponibilidade = total de exemplares - empréstimos ativos.

    Pode ser negativa? Não deveria, mas nunca deixamos o número passar de
    total.
    """
    return max(0, exemplares_total - emprestimos_ativos)


def esta_atrasado(emprestimo: Emprestimo, hoje: datetime) -> bool:
    """Um empréstimo está atrasado quando está ATIVO e venceu antes de hoje.

    "Vence hoje" não conta como atraso.
    """
    if emprestimo.status != StatusEmprestimo.ATIVO:
        return False
    return inicio_do_dia(emprestimo.data_prevista) < inicio_do_dia(hoje)


def dias_de_atraso(data_prevista: datetime, hoje: datetime) -> int:
    """Quantos dias inteiros já passaram do vencimento (0 se ainda não venceu)."""
    diferenca = inicio_do_dia(hoje) - inicio_do_dia(data_prevista)
    return max(0, diferenca.days)


@dataclass(frozen=True)
class EstadoParaEmprestar:
    """Estado atual do livro + usuário, coletado antes de decidir o empréstimo."""

    exemplares_total: int
    emprestimos_ativos_do_livro: int
    emprestimos_ativos_do_usuario: int
    usuario_tem_atraso: bool


@dataclass(frozen=True)
class EstadoParaAtualizarLivro:
    """Estado do livro no momento de editar a quantidade de exemplares."""

    exemplares_total: int
    emprestimos_ativos: int


def validar_atualizacao_de_livro(estado: EstadoParaAtualizarLivro) -> None:
    """Não deixa reduzir os exemplares abaixo do que já está emprestado.

    Ex.: o livro tem 3 exemplares e 2 ativos; o mínimo agora é 2.
    """
    if estado.exemplares_total < estado.emprestimos_ativos:
        raise erros.exemplares_abaixo_dos_emprestimos(
            estado.exemplares_total,
            estado.emprestimos_ativos,
        )


class ModoDeExclusao(StrEnum):
    """Maneiras de excluir um cadastro."""

    APAGAR = "APAGAR"
    MANTER_HISTORICO = "MANTER_HISTORICO"


def decidir_modo_de_exclusao(emprestimos_registrados: int) -> ModoDeExclusao:
    """Decide o que fazer ao excluir livro ou usuário.

    Sem empréstimos: apaga a linha de verdade (não há histórico para guardar).
    Com empréstimos: NÃO apaga. Só marca `excluido_em`, para o histórico
    continuar mostrando qual livro/usuário participou do empréstimo.

    A regra é pura de propósito: dá para testar sem banco.
    """
    if emprestimos_registrados > 0:
        return ModoDeExclusao.MANTER_HISTORICO
    return ModoDeExclusao.APAGAR


def validar_emprestimo(
    estado: EstadoParaEmprestar,
    limite_de_emprestimos: int = LIMITE_PADRAO_DE_EMPRESTIMOS,
) -> None:
    """Valida as três regras de empréstimo na ordem em que fazem sentido.

    Primeiro "tem livro?", depois "você está em atraso?", depois "atingiu o
    limite?". Lançar erro em vez de retornar booleano é proposital: o caso de
    uso não precisa montar if/else, e a mensagem já sai pronta para a API.
    """
    disponiveis = calcular_disponiveis(
        estado.exemplares_total,
        estado.emprestimos_ativos_do_livro,
    )

    if disponiveis <= 0:
        raise erros.livro_indisponivel()
    if estado.usuario_tem_atraso:
        raise erros.usuario_com_atraso()
    if estado.emprestimos_ativos_do_usuario >= limite_de_emprestimos:
        raise erros.limite_atingido(limite_de_emprestimos)
