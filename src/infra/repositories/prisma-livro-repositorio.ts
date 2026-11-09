import type { PrismaClient } from '@prisma/client'
import type {
  DadosNovoLivro,
  LivroRepositorio,
} from '../../domain/repositorios'
import type { Livro, LivroComDisponibilidade } from '../../domain/entidades'
import type { EstadoParaAtualizarLivro } from '../../domain/regras'
import { calcularDisponiveis } from '../../domain/regras'
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

  async buscarPorId(id: string): Promise<Livro | null> {
    return this.prisma.livro.findUnique({ where: { id } })
  }

  /**
   * Lista os livros já com a contagem de empréstimos ativos.
   *
   * `_count` com `where` faz o Postgres contar apenas os ATIVOS em uma única
   * consulta, em vez de carregar todos os empréstimos para a memória.
   */
  async listarComDisponibilidade(): Promise<LivroComDisponibilidade[]> {
    const livros = await this.prisma.livro.findMany({
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
        WHERE id = ${id}::uuid
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
   * Exclui o livro somente se não houver nenhum empréstimo ligado a ele.
   * A checagem e o delete acontecem na mesma transação, com a linha travada.
   */
  async excluirComBloqueio(
    id: string,
    validar: (emprestimosRegistrados: number) => void,
  ): Promise<void> {
    await this.prisma.$transaction(async (tx) => {
      const linhas = await tx.$queryRaw<Array<{ id: string }>>`
        SELECT id
        FROM livros
        WHERE id = ${id}::uuid
        FOR UPDATE
      `

      if (!linhas[0]) throw erros.livroNaoEncontrado()

      const emprestimosRegistrados = await tx.emprestimo.count({
        where: { livroId: id },
      })

      validar(emprestimosRegistrados)

      await tx.livro.delete({ where: { id } })
    })
  }
}
