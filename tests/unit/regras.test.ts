import { describe, expect, it } from 'vitest'
import {
  calcularDataPrevista,
  calcularDisponiveis,
  estaAtrasado,
  inicioDoDia,
  validarEmprestimo,
} from '../../src/domain/regras'
import type { ErroDeDominio } from '../../src/domain/erros'

/**
 * Testes das regras puras.
 *
 * Cada teste segue o mesmo formato: prepara o cenário, executa a regra e
 * verifica o resultado. Sem banco, sem mock de HTTP, sem espera.
 */

/** Executa a função e devolve o código do erro lançado (ou 'SEM_ERRO'). */
function codigoDoErro(funcao: () => void): string {
  try {
    funcao()
    return 'SEM_ERRO'
  } catch (erro) {
    return (erro as ErroDeDominio).codigo
  }
}

describe('inicioDoDia', () => {
  it('zera horas, minutos e segundos em UTC', () => {
    const resultado = inicioDoDia(new Date('2026-01-05T18:45:12.000Z'))

    expect(resultado.toISOString()).toBe('2026-01-05T00:00:00.000Z')
  })
})

describe('calcularDataPrevista', () => {
  it('soma o prazo em dias ao dia do empréstimo', () => {
    const prevista = calcularDataPrevista(new Date('2026-01-05T14:30:00.000Z'), 14)

    expect(prevista.toISOString()).toBe('2026-01-19T00:00:00.000Z')
  })

  it('atravessa a virada do mês corretamente', () => {
    const prevista = calcularDataPrevista(new Date('2026-01-25T10:00:00.000Z'), 14)

    expect(prevista.toISOString()).toBe('2026-02-08T00:00:00.000Z')
  })

  it('respeita um prazo diferente do padrão', () => {
    const prevista = calcularDataPrevista(new Date('2026-03-01T10:00:00.000Z'), 7)

    expect(prevista.toISOString()).toBe('2026-03-08T00:00:00.000Z')
  })
})

describe('calcularDisponiveis', () => {
  it('desconta os empréstimos ativos', () => {
    expect(calcularDisponiveis(3, 1)).toBe(2)
  })

  it('nunca devolve número negativo', () => {
    expect(calcularDisponiveis(1, 5)).toBe(0)
  })
})

describe('estaAtrasado', () => {
  const emprestimo = {
    status: 'ATIVO' as const,
    dataPrevista: new Date('2026-01-19T00:00:00.000Z'),
  }

  it('não considera atrasado no próprio dia do vencimento', () => {
    expect(estaAtrasado(emprestimo, new Date('2026-01-19T23:59:00.000Z'))).toBe(false)
  })

  it('considera atrasado a partir do dia seguinte', () => {
    expect(estaAtrasado(emprestimo, new Date('2026-01-20T00:01:00.000Z'))).toBe(true)
  })

  it('empréstimo devolvido nunca está atrasado', () => {
    expect(
      estaAtrasado(
        { status: 'DEVOLVIDO', dataPrevista: emprestimo.dataPrevista },
        new Date('2026-02-01T00:00:00.000Z'),
      ),
    ).toBe(false)
  })
})

describe('validarEmprestimo', () => {
  const estadoBase = {
    exemplaresTotal: 1,
    emprestimosAtivosDoLivro: 0,
    emprestimosAtivosDoUsuario: 0,
    usuarioTemAtraso: false,
  }

  it('permite quando existe exemplar e o usuário está em dia', () => {
    expect(codigoDoErro(() => validarEmprestimo(estadoBase))).toBe('SEM_ERRO')
  })

  it('recusa quando não há exemplar disponível', () => {
    const codigo = codigoDoErro(() =>
      validarEmprestimo({ ...estadoBase, emprestimosAtivosDoLivro: 1 }),
    )

    expect(codigo).toBe('LIVRO_INDISPONIVEL')
  })

  it('recusa usuário com empréstimo em atraso', () => {
    const codigo = codigoDoErro(() =>
      validarEmprestimo({ ...estadoBase, usuarioTemAtraso: true }),
    )

    expect(codigo).toBe('USUARIO_COM_ATRASO')
  })

  it('recusa quando o usuário atingiu o limite de 3 ativos', () => {
    const codigo = codigoDoErro(() =>
      validarEmprestimo({ ...estadoBase, emprestimosAtivosDoUsuario: 3 }),
    )

    expect(codigo).toBe('LIMITE_ATINGIDO')
  })

  it('respeita um limite configurado diferente', () => {
    const codigo = codigoDoErro(() =>
      validarEmprestimo({ ...estadoBase, emprestimosAtivosDoUsuario: 2 }, 2),
    )

    expect(codigo).toBe('LIMITE_ATINGIDO')
  })
})
