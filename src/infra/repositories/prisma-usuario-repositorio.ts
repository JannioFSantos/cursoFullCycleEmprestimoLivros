import type { PrismaClient } from '@prisma/client'
import type { DadosNovoUsuario, UsuarioRepositorio } from '../../domain/repositorios'
import type { Usuario } from '../../domain/entidades'
import { erros } from '../../domain/erros'

/** Implementação do UsuarioRepositorio com Prisma. */
export class PrismaUsuarioRepositorio implements UsuarioRepositorio {
  constructor(private readonly prisma: PrismaClient) {}

  async criar(dados: DadosNovoUsuario): Promise<Usuario> {
    return this.prisma.usuario.create({ data: dados })
  }

  async buscarPorId(id: string): Promise<Usuario | null> {
    return this.prisma.usuario.findUnique({ where: { id } })
  }

  async listar(): Promise<Usuario[]> {
    return this.prisma.usuario.findMany({ orderBy: { nome: 'asc' } })
  }

  async atualizar(id: string, dados: DadosNovoUsuario): Promise<Usuario> {
    return this.prisma.usuario.update({ where: { id }, data: dados })
  }

  /**
   * Exclui o usuário somente se ele nunca tiver pegado um livro.
   * A transação trava a linha do usuário e conta os empréstimos antes.
   */
  async excluirComBloqueio(
    id: string,
    validar: (emprestimosRegistrados: number) => void,
  ): Promise<void> {
    await this.prisma.$transaction(async (tx) => {
      const linhas = await tx.$queryRaw<Array<{ id: string }>>`
        SELECT id
        FROM usuarios
        WHERE id = ${id}::uuid
        FOR UPDATE
      `

      if (!linhas[0]) throw erros.usuarioNaoEncontrado()

      const emprestimosRegistrados = await tx.emprestimo.count({
        where: { usuarioId: id },
      })

      validar(emprestimosRegistrados)

      await tx.usuario.delete({ where: { id } })
    })
  }
}
