import type { PrismaClient } from '@prisma/client'
import type {
  DadosNovoLivro,
  LivroRepositorio,
} from '../../domain/repositorios'
import type { Livro, LivroComDisponibilidade } from '../../domain/entidades'
import { calcularDisponiveis } from '../../domain/regras'

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
}
