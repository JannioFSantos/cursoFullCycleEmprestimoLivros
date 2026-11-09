import type { Emprestimo } from '../domain/entidades'
import type { EmprestimoRepositorio } from '../domain/repositorios'
import { erros } from '../domain/erros'
import type { Relogio } from '../domain/relogio'
import { relogioDoSistema } from '../domain/relogio'

/**
 * Caso de uso: registrar a devolução de um empréstimo.
 *
 * Duas regras:
 *  1. o empréstimo precisa existir (404 se não existir);
 *  2. não pode ser devolvido duas vezes (409).
 *
 * A data da devolução vem do relógio injetado, nunca de `new Date()` direto.
 */
export class DevolverEmprestimo {
  constructor(
    private readonly emprestimos: EmprestimoRepositorio,
    private readonly relogio: Relogio = relogioDoSistema,
  ) {}

  async executar(emprestimoId: string): Promise<Emprestimo> {
    const emprestimo = await this.emprestimos.buscarPorId(emprestimoId)
    if (!emprestimo) throw erros.emprestimoNaoEncontrado()

    // Devolver de novo não é erro do cliente? É conflito de estado, então 409.
    if (emprestimo.status === 'DEVOLVIDO') throw erros.emprestimoJaDevolvido()

    return this.emprestimos.registrarDevolucao(emprestimoId, this.relogio.agora())
  }
}
