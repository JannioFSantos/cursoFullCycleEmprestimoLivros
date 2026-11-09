import type { FastifyInstance } from 'fastify'
import type { UsuarioRepositorio } from '../../domain/repositorios'
import type { AtualizarUsuario } from '../../use-cases/atualizar-usuario'
import type { ExcluirUsuario } from '../../use-cases/excluir-usuario'
import { erros } from '../../domain/erros'
import { esquemaNovoUsuario, esquemaParametroId } from '../esquemas'
import { validar } from '../validacao'

export interface DependenciasDasRotasDeUsuarios {
  usuarios: UsuarioRepositorio
  atualizarUsuario: AtualizarUsuario
  excluirUsuario: ExcluirUsuario
}

/**
 * Rotas de usuários.
 *
 * POST /usuarios       -> cadastra (201)
 * GET  /usuarios       -> lista (200)
 * GET  /usuarios/:id   -> busca por id (200 ou 404)
 * PUT  /usuarios/:id   -> edita nome e e-mail (200)
 * DELETE /usuarios/:id -> exclui (204)
 */
export function registrarRotasDeUsuarios(
  app: FastifyInstance,
  dependencias: DependenciasDasRotasDeUsuarios,
): void {
  const { usuarios, atualizarUsuario, excluirUsuario } = dependencias

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

  app.put('/usuarios/:id', async (requisicao, resposta) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    const dados = validar(esquemaNovoUsuario, requisicao.body)
    const usuario = await atualizarUsuario.executar(id, dados)
    return resposta.status(200).send(usuario)
  })

  app.delete('/usuarios/:id', async (requisicao, resposta) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    await excluirUsuario.executar(id)
    return resposta.status(204).send()
  })
}
