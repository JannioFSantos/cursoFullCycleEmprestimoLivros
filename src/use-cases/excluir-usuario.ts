import type { UsuarioRepositorio } from '../domain/repositorios'
import type { Relogio } from '../domain/relogio'
import { relogioDoSistema } from '../domain/relogio'

/**
 * Caso de uso: excluir um usuário.
 *
 * Mesma proteção do livro: se já existe empréstimo, o usuário não é apagado
 * do banco. Ele só sai da lista, e o histórico continua mostrando quem pegou
 * cada livro.
 */
export class ExcluirUsuario {
  constructor(
    private readonly usuarios: UsuarioRepositorio,
    private readonly relogio: Relogio = relogioDoSistema,
  ) {}

  async executar(id: string): Promise<void> {
    await this.usuarios.excluir(id, this.relogio.agora())
  }
}
