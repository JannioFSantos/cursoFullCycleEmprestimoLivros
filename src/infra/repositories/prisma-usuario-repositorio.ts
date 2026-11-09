import type { PrismaClient } from '@prisma/client'
import type { DadosNovoUsuario, UsuarioRepositorio } from '../../domain/repositorios'
import type { Usuario } from '../../domain/entidades'

/** Implementação do UsuarioRepositorio com Prisma. */
export class PrismaUsuarioRepositorio implements UsuarioRepositorio {
  constructor(private readonly prisma: PrismaClient) {}

  async criar(dados: DadosNovoUsuario): Promise<Usuario> {
    return this.prisma.usuario.create({ data: dados })
  }

  async buscarPorId(id: string): Promise<Usuario | null> {
    return this.prisma.usuario.findUnique({ where: { id } })
  }
}
