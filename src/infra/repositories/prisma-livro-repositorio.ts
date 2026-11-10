import type { PrismaClient } from '@prisma/client'
import type {
  DadosNovoLivro,
  LivroRepositorio,
} from '../../domain/repositorios'
import type { Livro, LivroComDisponibilidade } from '../../domain/entidades'
import type { EstadoParaAtualizarLivro } from '../../domain/regras'
import { calcularDisponiveis, decidirModoDeExclusao } from '../../domain/regras'
import { erros } from '../../domain/erros'

/**
 * Implementação do LivroRepositorio usando Prisma.
 *
 * Note que esta classe só traduz operações de banco. Nenhuma regra de negócio
 * mora aqui — se você sentir vontade de escrever um `if` de negócio neste
 * arquivo, provavelmente ele pertence ao domínio.
 */
export class PrismaLivroRepositorio implements LivroRepositorio {
  constructor(private readonly prisma: PrismaClient) {}

  async criar(dados: DadosNovoLivro): Promise<Livro> {
    return this.prisma.livro.create({ data: dados })
  }

  /**
   * Livro marcado como excluído não conta mais como "encontrado".
   * Assim ele sai do catálogo e não pode receber empréstimo novo.
   */
  async buscarPorId(id: string): Promise<Livro | null> {
    return this.prisma.livro.findFirst({
      where: { id, excluidoEm: null },
    })
  }

  /**
   * Lista os livros já com a contagem de empréstimos ativos.
   *
   * `_count` com `where` faz o Postgres contar apenas os ATIVOS em uma única
   * consulta, em vez de carregar todos os empréstimos para a memória.
   */
  async listarComDisponibilidade(): Promise<LivroComDisponibilidade[]> {
    const livros = await this.prisma.livro.findMany({
      // Livros excluídos continuam no banco por causa do histórico, mas não
      // aparecem no catálogo.
      where: { excluidoEm: null },
      orderBy: { titulo: 'asc' },
      include: {
        _count: {
          select: { emprestimos: { where: { status: 'ATIVO' } } },
        },
      },
    })

    return livros.map(({ _count, ...livro }) => ({
      ...livro,
      emprestimosAtivos: _count.emprestimos,
      exemplaresDisponiveis: calcularDisponiveis(
        livro.exemplaresTotal,
        _count.emprestimos,
      ),
    }))
  }

  /**
   * Atualiza o livro dentro de uma transação.
   *
   * O FOR UPDATE trava a linha do livro. Assim, enquanto calculamos quantos
   * empréstimos ativos existem, ninguém consegue criar um empréstimo novo
   * para este livro. Sem o lock, uma requisição poderia emprestar entre a
   * contagem e o update, deixando exemplaresTotal menor que os ativos.
   */
  async atualizarComBloqueio(
    id: string,
    dados: DadosNovoLivro,
    validar: (estado: EstadoParaAtualizarLivro) => void,
  ): Promise<Livro> {
    return this.prisma.$transaction(async (tx) => {
      const linhas = await tx.$queryRaw<Array<{ id: string }>>`
        SELECT id
        FROM livros
        WHERE id = ${id}::uuid AND excluido_em IS NULL
        FOR UPDATE
      `

      if (!linhas[0]) throw erros.livroNaoEncontrado()

      const emprestimosAtivos = await tx.emprestimo.count({
        where: { livroId: id, status: 'ATIVO' },
      })

      // A regra é pura e mora no domínio; aqui só passamos o estado atual.
      validar({ exemplaresTotal: dados.exemplaresTotal, emprestimosAtivos })

      return tx.livro.update({ where: { id }, data: dados })
    })
  }

  /**
   * Exclui o livro com a linha travada.
   *
   * Se ele nunca teve empréstimo, apaga de verdade.
   * Se já teve, NÃO apaga: grava `excluidoEm`. O histórico de empréstimos
   * continua existindo e mostrando de qual livro se trata.
   *
   * A decisão é da função pura `decidirModoDeExclusao` (domínio), que também
   * é testada nos testes unitários.
   */
  async excluir(id: string, quando: Date): Promise<void> {
    await this.prisma.$transaction(async (tx) => {
      const linhas = await tx.$queryRaw<Array<{ id: string }>>`
        SELECT id
        FROM livros
        WHERE id = ${id}::uuid AND excluido_em IS NULL
        FOR UPDATE
      `

      if (!linhas[0]) throw erros.livroNaoEncontrado()

      const emprestimosRegistrados = await tx.emprestimo.count({
        where: { livroId: id },
      })

      if (decidirModoDeExclusao(emprestimosRegistrados) === 'APAGAR') {
        await tx.livro.delete({ where: { id } })
        return
      }

      await tx.livro.update({
        where: { id },
        data: { excluidoEm: quando },
      })
    })
  }
}
