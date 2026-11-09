import type { FastifyInstance } from 'fastify'
import type { UsuarioRepositorio } from '../../domain/repositorios'
import { erros } from '../../domain/erros'
import { esquemaNovoUsuario, esquemaParametroId } from '../esquemas'
import { validar } from '../validacao'

/** Rotas de usuários: cadastro e busca por id. */
export function registrarRotasDeUsuarios(
  app: FastifyInstance,
  usuarios: UsuarioRepositorio,
): void {
  app.post('/usuarios', async (requisicao, resposta) => {
    const dados = validar(esquemaNovoUsuario, requisicao.body)
    const usuario = await usuarios.criar(dados)
    return resposta.status(201).send(usuario)
  })

  // Lista usada pela tela de demonstração (select de usuário e tabela).
  app.get('/usuarios', async () => {
    return { itens: await usuarios.listar() }
  })

  app.get('/usuarios/:id', async (requisicao) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    const usuario = await usuarios.buscarPorId(id)

    // Se não existir, o erro handler transforma em 404 no formato padrão.
    if (!usuario) throw erros.usuarioNaoEncontrado()

    return usuario
  })
}
