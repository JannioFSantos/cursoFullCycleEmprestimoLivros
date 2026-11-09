import type { UsuarioRepositorio } from '../domain/repositorios'
import { validarExclusaoDeUsuario } from '../domain/regras'

/**
 * Caso de uso: excluir um usuário.
 *
 * Mesma proteção do livro: usuário que já pegou algum livro não é apagado,
 * porque isso apagaria o histórico de empréstimos dele.
 */
export class ExcluirUsuario {
  constructor(private readonly usuarios: UsuarioRepositorio) {}

  async executar(id: string): Promise<void> {
    await this.usuarios.excluirComBloqueio(id, validarExclusaoDeUsuario)
  }
}
