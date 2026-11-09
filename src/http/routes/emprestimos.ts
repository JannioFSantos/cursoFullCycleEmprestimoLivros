import type { FastifyInstance } from 'fastify'
import type { EmprestimoRepositorio } from '../../domain/repositorios'
import type { Relogio } from '../../domain/relogio'
import type { EmprestarLivro } from '../../use-cases/emprestar-livro'
import type { DevolverEmprestimo } from '../../use-cases/devolver-emprestimo'
import type { Metricas } from '../../observability/metricas'
import { ErroDeDominio } from '../../domain/erros'
import { esquemaNovoEmprestimo, esquemaParametroId } from '../esquemas'
import { validar } from '../validacao'

export interface DependenciasDasRotasDeEmprestimos {
  emprestarLivro: EmprestarLivro
  devolverEmprestimo: DevolverEmprestimo
  emprestimos: EmprestimoRepositorio
  relogio: Relogio
  metricas: Metricas
}

/**
 * Rotas de empréstimo — o fluxo principal do projeto.
 *
 * POST   /emprestimos              -> cria (201) ou recusa com regra (409)
 * PATCH  /emprestimos/:id/devolucao -> devolve (200)
 * GET    /emprestimos/atrasados    -> lista quem está devendo (200)
 */
export function registrarRotasDeEmprestimos(
  app: FastifyInstance,
  dependencias: DependenciasDasRotasDeEmprestimos,
): void {
  const { emprestarLivro, devolverEmprestimo, emprestimos, relogio, metricas } =
    dependencias

  app.post('/emprestimos', async (requisicao, resposta) => {
    const dados = validar(esquemaNovoEmprestimo, requisicao.body)

    try {
      const emprestimo = await emprestarLivro.executar(dados)
      metricas.emprestimos.inc({ resultado: 'criado' })
      return resposta.status(201).send(emprestimo)
    } catch (erro) {
      // Recusa de negócio (sem exemplar, atraso, limite) também é um número
      // que interessa: se disparar, algo mudou no comportamento dos usuários.
      if (erro instanceof ErroDeDominio) {
        metricas.emprestimos.inc({ resultado: 'recusado' })
      }
      // Repassa para o error handler central montar a resposta.
      throw erro
    }
  })

  app.patch('/emprestimos/:id/devolucao', async (requisicao, resposta) => {
    const { id } = validar(esquemaParametroId, requisicao.params)
    const emprestimo = await devolverEmprestimo.executar(id)
    return resposta.status(200).send(emprestimo)
  })

  app.get('/emprestimos/atrasados', async () => {
    // Usa o mesmo relógio injetado: em teste conseguimos "viajar no tempo".
    return { itens: await emprestimos.listarAtrasados(relogio.agora()) }
  })
}
