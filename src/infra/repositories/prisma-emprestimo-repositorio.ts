import type { PrismaClient } from '@prisma/client'
import type {
  DadosNovoEmprestimo,
  EmprestimoRepositorio,
} from '../../domain/repositorios'
import type { Emprestimo, EmprestimoDetalhado } from '../../domain/entidades'
import type { EstadoParaEmprestar } from '../../domain/regras'
import { inicioDoDia } from '../../domain/regras'
import { erros } from '../../domain/erros'

/**
 * Implementação do EmprestimoRepositorio com Prisma.
 *
 * É o arquivo mais "delicado" do projeto, porque é onde garantimos que dois
 * pedidos simultâneos não levem o mesmo último exemplar. Leia o ADR 0001
 * antes de mexer aqui.
 */
export class PrismaEmprestimoRepositorio implements EmprestimoRepositorio {
  constructor(private readonly prisma: PrismaClient) {}

  async criarComBloqueio(
    dados: DadosNovoEmprestimo,
    validar: (estado: EstadoParaEmprestar) => void,
  ): Promise<Emprestimo> {
    // $transaction abre uma transação: ou tudo confirma, ou tudo é desfeito.
    return this.prisma.$transaction(
      async (tx) => {
        // ---------------------------------------------------------------
        // 1) SELECT ... FOR UPDATE
        //
        // Trava a linha do livro até o fim da transação. Se outra requisição
        // tentar emprestar o mesmo livro ao mesmo tempo, ela espera aqui.
        // É isso que impede o "último exemplar vendido duas vezes".
        //
        // O `::uuid` é necessário porque o Prisma envia o parâmetro como
        // texto e o Postgres não compara uuid com text sozinho.
        // ---------------------------------------------------------------
        const livros = await tx.$queryRaw<
          Array<{ id: string; exemplares_total: number }>
        >`
          SELECT id, exemplares_total
          FROM livros
          WHERE id = ${dados.livroId}::uuid
          FOR UPDATE
        `

        const livro = livros[0]
        if (!livro) throw erros.livroNaoEncontrado()

        // Trava também o usuário, sempre DEPOIS do livro. Manter a mesma
        // ordem em todas as transações evita deadlock (um espera pelo outro
        // para sempre). Se invertêssemos a ordem em algum lugar, o Postgres
        // poderia detectar e matar uma das transações.
        const usuarios = await tx.$queryRaw<Array<{ id: string }>>`
          SELECT id
          FROM usuarios
          WHERE id = ${dados.usuarioId}::uuid
          FOR UPDATE
        `

        if (!usuarios[0]) throw erros.usuarioNaoEncontrado()

        // ---------------------------------------------------------------
        // 2) Contagens dentro da transação, já com a linha travada.
        //    Como ninguém mais consegue gravar nesse livro agora, estes
        //    números não mudam até o commit.
        // ---------------------------------------------------------------
        const emprestimosAtivosDoLivro = await tx.emprestimo.count({
          where: { livroId: dados.livroId, status: 'ATIVO' },
        })

        const emprestimosAtivosDoUsuario = await tx.emprestimo.count({
          where: { usuarioId: dados.usuarioId, status: 'ATIVO' },
        })

        const emprestimoEmAtraso = await tx.emprestimo.findFirst({
          where: {
            usuarioId: dados.usuarioId,
            status: 'ATIVO',
            dataPrevista: { lt: inicioDoDia(dados.dataEmprestimo) },
          },
          select: { id: true },
        })

        // ---------------------------------------------------------------
        // 3) A regra de negócio é a MESMA função pura testada nos unitários.
        //    Se ela lançar erro, a transação é desfeita automaticamente.
        // ---------------------------------------------------------------
        validar({
          exemplaresTotal: livro.exemplares_total,
          emprestimosAtivosDoLivro,
          emprestimosAtivosDoUsuario,
          usuarioTemAtraso: emprestimoEmAtraso !== null,
        })

        // 4) Só chega aqui quem passou em todas as regras.
        return tx.emprestimo.create({
          data: {
            livroId: dados.livroId,
            usuarioId: dados.usuarioId,
            status: 'ATIVO',
            dataEmprestimo: dados.dataEmprestimo,
            dataPrevista: dados.dataPrevista,
          },
        })
      },
      // Tempo máximo para esperar lock/executar a transação. Em caso de
      // timeout o Prisma aborta e a API responde 500 (erro real, não 409).
      { timeout: 10_000 },
    )
  }

  async buscarPorId(id: string): Promise<Emprestimo | null> {
    return this.prisma.emprestimo.findUnique({ where: { id } })
  }

  async registrarDevolucao(id: string, dataDevolucao: Date): Promise<Emprestimo> {
    return this.prisma.emprestimo.update({
      where: { id },
      data: { status: 'DEVOLVIDO', dataDevolucao },
    })
  }

  /**
   * Empréstimos ativos com data prevista anterior a hoje.
   * Ordenados do mais antigo para o mais recente, porque quem está devendo
   * há mais tempo é a prioridade de cobrança.
   */
  async listarAtrasados(hoje: Date): Promise<EmprestimoDetalhado[]> {
    return this.prisma.emprestimo.findMany({
      where: {
        status: 'ATIVO',
        dataPrevista: { lt: inicioDoDia(hoje) },
      },
      orderBy: { dataPrevista: 'asc' },
      include: {
        livro: { select: { id: true, titulo: true, autor: true } },
        usuario: { select: { id: true, nome: true, email: true } },
      },
    })
  }

  /**
   * Lista todos os empréstimos com livro e usuário juntos.
   * A tela de demonstração usa isso para mostrar "quem pegou qual livro".
   */
  async listarDetalhados(): Promise<EmprestimoDetalhado[]> {
    return this.prisma.emprestimo.findMany({
      orderBy: { dataEmprestimo: 'desc' },
      include: {
        livro: { select: { id: true, titulo: true, autor: true } },
        usuario: { select: { id: true, nome: true, email: true } },
      },
    })
  }
}
