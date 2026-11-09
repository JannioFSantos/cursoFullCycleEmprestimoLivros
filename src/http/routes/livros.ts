import type { FastifyInstance } from 'fastify'
import type { LivroRepositorio } from '../../domain/repositorios'
import type { AtualizarLivro } from '../../use-cases/atualizar-livro'
import type { ExcluirLivro } from '../../use-cases/excluir-livro'
import { esquemaNovoLivro, esquemaParametroId } from '../esquemas'
import { validar } from '../validacao'

export interface DependenciasDasRotasDeLivros {
  livros: LivroRepositorio
  atualizarLivro: AtualizarLivro
  excluirLivro: ExcluirLivro
}

/**
 * Rotas de livros.
 *
 * POST   /livros       -> cadastra (201)
 * GET    /livros       -> lista com disponibilidade (200)
 * PUT    /livros/:id   -> edita todos os campos (200)
 * DELETE /livros/:id   -> exclui (204)
 *
 * Repare que a rota é "burra" de propósito: valida a entrada, chama o caso de
 * uso/repositório e devolve. Regra de negócio fica no domínio/use case.
 */
export function registrarRotasDeLivros(
  app: FastifyInstance,
  dependencias: DependenciasDasRotasDeLivros,
): void {
  const { livros, atualizarLivro, excluirLivro } = dependencias

  app.post('/livros', async (requisicao, resposta) => {
    const dados = validar(esquemaNovoLivro, requisicao.body)
    const livro = await livros.criar(dados)

    // 201 Created: a convenção para "criei um recurso novo".
    return resposta.status(201).send(livro)
  })

  app.get('/livros', async () => {
    return { itens: await livros.listarComDisponibilidade() }
  })

  app.put('/livros/:id', async (requisicao, resposta) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    const dados = validar(esquemaNovoLivro, requisicao.body)
    const livro = await atualizarLivro.executar(id, dados)
    return resposta.status(200).send(livro)
  })

  app.delete('/livros/:id', async (requisicao, resposta) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    await excluirLivro.executar(id)

    // 204 No Content: deu certo e não há corpo para devolver.
    return resposta.status(204).send()
  })
}
