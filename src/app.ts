import { randomUUID } from 'node:crypto'
import Fastify, {
  type FastifyInstance,
  type FastifyServerOptions,
} from 'fastify'
import type { PrismaClient } from '@prisma/client'

import { env } from './config/env'
import type { Relogio } from './domain/relogio'
import { relogioDoSistema } from './domain/relogio'
import {
  LIMITE_PADRAO_DE_EMPRESTIMOS,
  PRAZO_PADRAO_EM_DIAS,
} from './domain/regras'

import { PrismaLivroRepositorio } from './infra/repositories/prisma-livro-repositorio'
import { PrismaUsuarioRepositorio } from './infra/repositories/prisma-usuario-repositorio'
import { PrismaEmprestimoRepositorio } from './infra/repositories/prisma-emprestimo-repositorio'

import { EmprestarLivro } from './use-cases/emprestar-livro'
import { DevolverEmprestimo } from './use-cases/devolver-emprestimo'

import { criarMetricas, criarRegistroDeMetricas } from './observability/metricas'
import { registrarTratamentoDeErros } from './http/erro-handler'
import { registrarRotasDeLivros } from './http/routes/livros'
import { registrarRotasDeUsuarios } from './http/routes/usuarios'
import { registrarRotasDeEmprestimos } from './http/routes/emprestimos'

export interface DependenciasDoApp {
  prisma: PrismaClient
  /** Injetável para testes; em produção é o relógio do sistema. */
  relogio?: Relogio
  prazoEmDias?: number
  limiteDeEmprestimos?: number
}

/**
 * Monta a aplicação Fastify com todas as dependências ligadas.
 *
 * Esta função é o "cabo de força" do projeto: cria repositórios, casos de uso
 * e rotas, e devolve o app pronto para escutar. Ela NÃO chama listen() — quem
 * faz isso é o server.ts. Essa separação é o que permite testar a API inteira
 * com `app.inject()` sem abrir uma porta de rede.
 */
export function criarApp(dependencias: DependenciasDoApp): FastifyInstance {
  const { prisma } = dependencias
  const relogio = dependencias.relogio ?? relogioDoSistema
  const prazoEmDias = dependencias.prazoEmDias ?? PRAZO_PADRAO_EM_DIAS
  const limiteDeEmprestimos =
    dependencias.limiteDeEmprestimos ?? LIMITE_PADRAO_DE_EMPRESTIMOS

  const app = Fastify({
    logger: criarConfiguracaoDeLog(),
    // Desligamos o log automático de requisição para logar UMA linha nossa,
    // com os campos que realmente importam (rota, status, duração).
    // Obs.: em Fastify 5.12 esta opção emite um aviso de depreciação; ela
    // continua funcionando até o Fastify 6, quando vira `logController`.
    disableRequestLogging: true,
    // Correlation id: se o cliente mandar x-request-id, respeitamos; senão
    // geramos um UUID. Esse id aparece em todos os logs daquela requisição.
    genReqId: (requisicao) =>
      (requisicao.headers['x-request-id'] as string | undefined) ?? randomUUID(),
  })

  // ------------------------- Observabilidade -------------------------------
  const registro = criarRegistroDeMetricas()
  const metricas = criarMetricas(registro)

  // Rotas de infraestrutura não entram nas métricas nem nos logs de acesso:
  // o healthcheck do Coolify bate a cada 30s e poluiria tudo.
  const rotasIgnoradas = new Set(['/health', '/metrics', '/'])

  app.addHook('onResponse', async (requisicao, resposta) => {
    const rota = requisicao.routeOptions.url ?? 'desconhecida'
    if (rotasIgnoradas.has(rota)) return

    const duracaoMs = resposta.elapsedTime

    metricas.duracaoHttp.observe(
      {
        metodo: requisicao.method,
        rota,
        status: String(resposta.statusCode),
      },
      duracaoMs / 1000,
    )

    // Log estruturado (JSON em produção): fácil de filtrar no Coolify.
    requisicao.log.info(
      {
        requisicaoId: requisicao.id,
        metodo: requisicao.method,
        rota,
        status: resposta.statusCode,
        duracaoMs: Number(duracaoMs.toFixed(1)),
      },
      'requisicao_concluida',
    )
  })

  // --------------------------- Infraestrutura ------------------------------
  app.get('/health', async (requisicao, resposta) => {
    try {
      // Não basta o processo estar vivo: a API só é útil se o banco responde.
      await prisma.$queryRaw`SELECT 1`
      return {
        status: 'ok',
        uptimeSegundos: Math.round(process.uptime()),
      }
    } catch (erro) {
      requisicao.log.error({ err: erro }, 'healthcheck_banco_indisponivel')
      return resposta.status(503).send({
        status: 'degradado',
        banco: 'indisponivel',
      })
    }
  })

  app.get('/metrics', async (_requisicao, resposta) => {
    resposta.type(registro.contentType)
    return registro.metrics()
  })

  app.get('/', async () => ({
    nome: 'API de Empréstimos de Biblioteca',
    nivel: 'Projeto B — Full Cycle',
    rotas: [
      'GET /health',
      'GET /metrics',
      'POST /livros',
      'GET /livros',
      'POST /usuarios',
      'POST /emprestimos',
      'PATCH /emprestimos/:id/devolucao',
      'GET /emprestimos/atrasados',
    ],
  }))

  // ------------------------------ Domínio ----------------------------------
  const livros = new PrismaLivroRepositorio(prisma)
  const usuarios = new PrismaUsuarioRepositorio(prisma)
  const emprestimos = new PrismaEmprestimoRepositorio(prisma)

  const emprestarLivro = new EmprestarLivro(
    livros,
    usuarios,
    emprestimos,
    relogio,
    prazoEmDias,
    limiteDeEmprestimos,
  )
  const devolverEmprestimo = new DevolverEmprestimo(emprestimos, relogio)

  // ------------------------------- Rotas -----------------------------------
  registrarRotasDeLivros(app, livros)
  registrarRotasDeUsuarios(app, usuarios)
  registrarRotasDeEmprestimos(app, {
    emprestarLivro,
    devolverEmprestimo,
    emprestimos,
    relogio,
    metricas,
  })

  registrarTratamentoDeErros(app)

  return app
}

/**
 * Configuração do logger (pino, embutido no Fastify).
 *
 * - produção: JSON puro, que é o formato que ferramentas de log entendem.
 * - desenvolvimento: pino-pretty, legível no terminal.
 * - teste: desligado, para não poluir a saída do Vitest.
 */
function criarConfiguracaoDeLog(): FastifyServerOptions['logger'] {
  if (env.NODE_ENV === 'test') return false

  const desenvolvimento = env.NODE_ENV === 'development'

  return {
    level: env.LOG_LEVEL,
    // Nunca logamos cabeçalhos sensíveis.
    redact: {
      paths: ['req.headers.authorization', 'req.headers.cookie'],
      remove: true,
    },
    ...(desenvolvimento
      ? {
          transport: {
            target: 'pino-pretty',
            options: {
              translateTime: 'HH:MM:ss',
              ignore: 'pid,hostname',
              singleLine: true,
            },
          },
        }
      : {}),
  }
}
