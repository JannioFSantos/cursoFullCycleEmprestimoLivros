"""Testes das regras puras do domínio."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.entidades import Emprestimo, StatusEmprestimo
from app.domain.erros import ErroDeDominio
from app.domain.regras import (
    EstadoParaEmprestar,
    calcular_data_prevista,
    calcular_disponiveis,
    decidir_modo_de_exclusao,
    dias_de_atraso,
    esta_atrasado,
    inicio_do_dia,
    validar_emprestimo,
)
from tests.fakes import criar_livro_fake, criar_usuario_fake


def codigo_do_erro(funcao) -> str:
    """Executa a função e devolve o código do erro lançado (ou 'SEM_ERRO')."""
    try:
        funcao()
    except ErroDeDominio as erro:
        return erro.codigo
    return "SEM_ERRO"


def test_inicio_do_dia_zera_horas_minutos_e_segundos():
    resultado = inicio_do_dia(datetime(2026, 1, 5, 18, 45, 12))
    assert resultado == datetime(2026, 1, 5)


def test_calcular_data_prevista_soma_o_prazo_ao_dia_do_emprestimo():
    prevista = calcular_data_prevista(datetime(2026, 1, 5, 14, 30), 14)
    assert prevista == datetime(2026, 1, 19)


def test_calcular_data_prevista_atravessa_a_virada_do_mes():
    prevista = calcular_data_prevista(datetime(2026, 1, 25, 10), 14)
    assert prevista == datetime(2026, 2, 8)


def test_calcular_data_prevista_respeita_prazo_diferente():
    prevista = calcular_data_prevista(datetime(2026, 3, 1, 10), 7)
    assert prevista == datetime(2026, 3, 8)


def test_calcular_disponiveis_desconta_emprestimos_ativos():
    assert calcular_disponiveis(3, 1) == 2


def test_calcular_disponiveis_nunca_devolve_negativo():
    assert calcular_disponiveis(1, 5) == 0


def _emprestimo(status: StatusEmprestimo = StatusEmprestimo.ATIVO):
    livro = criar_livro_fake()
    usuario = criar_usuario_fake()
    return Emprestimo(
        id=livro.id,
        livro_id=livro.id,
        usuario_id=usuario.id,
        status=status,
        data_emprestimo=datetime(2026, 1, 5),
        data_prevista=datetime(2026, 1, 19),
    )


def test_nao_considera_atrasado_no_proprio_dia_do_vencimento():
    assert not esta_atrasado(_emprestimo(), datetime(2026, 1, 19, 23, 59))


def test_considera_atrasado_a_partir_do_dia_seguinte():
    assert esta_atrasado(_emprestimo(), datetime(2026, 1, 20, 0, 1))


def test_emprestimo_devolvido_nunca_esta_atrasado():
    emprestimo = _emprestimo(StatusEmprestimo.DEVOLVIDO)
    assert not esta_atrasado(emprestimo, datetime(2026, 2, 1))


def test_dias_de_atraso_conta_dias_inteiros_desde_o_vencimento():
    assert dias_de_atraso(datetime(2026, 1, 19), datetime(2026, 2, 4, 12)) == 16


def test_dias_de_atraso_e_zero_quando_ainda_nao_venceu():
    assert dias_de_atraso(datetime(2026, 1, 19), datetime(2026, 1, 10)) == 0


ESTADO_BASE = dict(
    exemplares_total=1,
    emprestimos_ativos_do_livro=0,
    emprestimos_ativos_do_usuario=0,
    usuario_tem_atraso=False,
)


def test_permite_quando_existe_exemplar_e_usuario_em_dia():
    assert codigo_do_erro(
        lambda: validar_emprestimo(EstadoParaEmprestar(**ESTADO_BASE))
    ) == "SEM_ERRO"


def test_recusa_quando_nao_ha_exemplar_disponivel():
    estado = EstadoParaEmprestar(**{**ESTADO_BASE, "emprestimos_ativos_do_livro": 1})
    assert codigo_do_erro(lambda: validar_emprestimo(estado)) == "LIVRO_INDISPONIVEL"


def test_recusa_usuario_com_emprestimo_em_atraso():
    estado = EstadoParaEmprestar(**{**ESTADO_BASE, "usuario_tem_atraso": True})
    assert codigo_do_erro(lambda: validar_emprestimo(estado)) == "USUARIO_COM_ATRASO"


def test_recusa_quando_usuario_atingiu_o_limite_padrao():
    estado = EstadoParaEmprestar(
        **{**ESTADO_BASE, "emprestimos_ativos_do_usuario": 3}
    )
    assert codigo_do_erro(lambda: validar_emprestimo(estado)) == "LIMITE_ATINGIDO"


def test_respeita_um_limite_configurado_diferente():
    estado = EstadoParaEmprestar(
        **{**ESTADO_BASE, "emprestimos_ativos_do_usuario": 2}
    )
    assert codigo_do_erro(lambda: validar_emprestimo(estado, 2)) == "LIMITE_ATINGIDO"


def test_apaga_de_verdade_quando_nao_existe_emprestimo():
    assert decidir_modo_de_exclusao(0).value == "APAGAR"


@pytest.mark.parametrize("quantidade", [1, 5])
def test_preserva_historico_quando_existe_emprestimo(quantidade):
    assert decidir_modo_de_exclusao(quantidade).value == "MANTER_HISTORICO"
