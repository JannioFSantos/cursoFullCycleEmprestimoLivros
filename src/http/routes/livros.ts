import type { FastifyInstance } from 'fastify'
import type { LivroRepositorio } from '../../domain/repositorios'
import { esquemaNovoLivro } from '../esquemas'
import { validar } from '../validacao'

/**
 * Rotas de livros.
 *
 * Repare que a rota é "burra" de propósito: valida a entrada, chama o
 * repositório e devolve. Regra de negócio fica no domínio/use case.
 */
export function registrarRotasDeLivros(
  app: FastifyInstance,
  livros: LivroRepositorio,
): void {
  app.post('/livros', async (requisicao, resposta) => {
    const dados = validar(esquemaNovoLivro, requisicao.body)
    const livro = await livros.criar(dados)

    // 201 Created: a convenção para "criei um recurso novo".
    return resposta.status(201).send(livro)
  })

  app.get('/livros', async () => {
    return { itens: await livros.listarComDisponibilidade() }
  })
}
