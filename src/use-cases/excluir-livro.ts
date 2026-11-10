import type { LivroRepositorio } from '../domain/repositorios'
import type { Relogio } from '../domain/relogio'
import { relogioDoSistema } from '../domain/relogio'

/**
 * Caso de uso: excluir um livro.
 *
 * A regra de "apagar de verdade ou só marcar como excluído" está no domínio
 * (`decidirModoDeExclusao`) e é aplicada pelo repositório dentro de uma
 * transação. Livro com empréstimos sai do catálogo, mas o histórico continua
 * aparecendo na lista de empréstimos.
 *
 * A data da exclusão vem do relógio injetado, igual à data de devolução.
 */
export class ExcluirLivro {
  constructor(
    private readonly livros: LivroRepositorio,
    private readonly relogio: Relogio = relogioDoSistema,
  ) {}

  async executar(id: string): Promise<void> {
    await this.livros.excluir(id, this.relogio.agora())
  }
}
