import type { PrismaClient } from '@prisma/client'
import type { DadosNovoUsuario, UsuarioRepositorio } from '../../domain/repositorios'
import type { Usuario } from '../../domain/entidades'
import { decidirModoDeExclusao } from '../../domain/regras'
import { erros } from '../../domain/erros'

/** Implementação do UsuarioRepositorio com Prisma. */
export class PrismaUsuarioRepositorio implements UsuarioRepositorio {
  constructor(private readonly prisma: PrismaClient) {}

  async criar(dados: DadosNovoUsuario): Promise<Usuario> {
    return this.prisma.usuario.create({ data: dados })
  }

  /** Usuário marcado como excluído não é mais encontrado (nem pode pegar livro). */
  async buscarPorId(id: string): Promise<Usuario | null> {
    return this.prisma.usuario.findFirst({
      where: { id, excluidoEm: null },
    })
  }

  async listar(): Promise<Usuario[]> {
    return this.prisma.usuario.findMany({
      // Usuários excluídos continuam no banco por causa do histórico, mas não
      // aparecem na lista.
      where: { excluidoEm: null },
      orderBy: { nome: 'asc' },
    })
  }

  async atualizar(id: string, dados: DadosNovoUsuario): Promise<Usuario> {
    // updateMany com `excluidoEm: null` evita editar um usuário que acabou de
    // ser excluído por outra requisição.
    const resultado = await this.prisma.usuario.updateMany({
      where: { id, excluidoEm: null },
      data: dados,
    })

    if (resultado.count === 0) throw erros.usuarioNaoEncontrado()

    return this.prisma.usuario.findUniqueOrThrow({ where: { id } })
  }

  /**
   * Exclui o usuário com a linha travada.
   *
   * Sem empréstimos: apaga de verdade.
   * Com empréstimos: só grava `excluidoEm`, para o histórico continuar
   * mostrando quem pegou cada livro. A decisão vem do domínio.
   */
  async excluir(id: string, quando: Date): Promise<void> {
    await this.prisma.$transaction(async (tx) => {
      const linhas = await tx.$queryRaw<Array<{ id: string }>>`
        SELECT id
        FROM usuarios
        WHERE id = ${id}::uuid AND excluido_em IS NULL
        FOR UPDATE
      `

      if (!linhas[0]) throw erros.usuarioNaoEncontrado()

      const emprestimosRegistrados = await tx.emprestimo.count({
        where: { usuarioId: id },
      })

      if (decidirModoDeExclusao(emprestimosRegistrados) === 'APAGAR') {
        await tx.usuario.delete({ where: { id } })
        return
      }

      await tx.usuario.update({
        where: { id },
        data: { excluidoEm: quando },
      })
    })
  }
}
