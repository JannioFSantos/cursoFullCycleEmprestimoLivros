import type { Livro } from '../domain/entidades'
import type { DadosNovoLivro, LivroRepositorio } from '../domain/repositorios'
import { validarAtualizacaoDeLivro } from '../domain/regras'

/**
 * Caso de uso: editar um livro.
 *
 * A regra importante é não deixar a quantidade de exemplares ficar menor do
 * que o número de empréstimos ativos. Quem garante que a contagem e a gravação
 * acontecem juntas é o repositório (transação com FOR UPDATE).
 */
export class AtualizarLivro {
  constructor(private readonly livros: LivroRepositorio) {}

  async executar(id: string, dados: DadosNovoLivro): Promise<Livro> {
    return this.livros.atualizarComBloqueio(id, dados, validarAtualizacaoDeLivro)
  }
}
