import type { LivroRepositorio } from '../domain/repositorios'
import { validarExclusaoDeLivro } from '../domain/regras'

/**
 * Caso de uso: excluir um livro.
 *
 * Só permite excluir livro que nunca teve empréstimo. Se tivesse, apagar o
 * livro apagaria também o histórico de quem pegou. A regra fica no domínio
 * (`validarExclusaoDeLivro`) e o repositório faz a checagem + delete juntos.
 */
export class ExcluirLivro {
  constructor(private readonly livros: LivroRepositorio) {}

  async executar(id: string): Promise<void> {
    await this.livros.excluirComBloqueio(id, validarExclusaoDeLivro)
  }
}
