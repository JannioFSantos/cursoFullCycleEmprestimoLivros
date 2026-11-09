import type { Usuario } from '../domain/entidades'
import type { DadosNovoUsuario, UsuarioRepositorio } from '../domain/repositorios'
import { erros } from '../domain/erros'

/**
 * Caso de uso: editar um usuário.
 *
 * Verificamos se ele existe antes de atualizar para devolver 404 no formato
 * padrão, em vez de deixar o Prisma estourar um erro interno. E-mail repetido
 * continua sendo barrado pelo índice único do banco (409 VALOR_JA_CADASTRADO).
 */
export class AtualizarUsuario {
  constructor(private readonly usuarios: UsuarioRepositorio) {}

  async executar(id: string, dados: DadosNovoUsuario): Promise<Usuario> {
    const usuario = await this.usuarios.buscarPorId(id)
    if (!usuario) throw erros.usuarioNaoEncontrado()

    return this.usuarios.atualizar(id, dados)
  }
}
