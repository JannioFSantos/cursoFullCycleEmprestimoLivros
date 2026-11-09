import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import Fastify, {
  type FastifyInstance,
  type FastifyServerOptions,
} from 'fastify'
import type { PrismaClient } from '@prisma/client'
import swagger from '@fastify/swagger'
import swaggerUi from '@fastify/swagger-ui'

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
import { AtualizarLivro } from './use-cases/atualizar-livro'
import { ExcluirLivro } from './use-cases/excluir-livro'
import { AtualizarUsuario } from './use-cases/atualizar-usuario'
import { ExcluirUsuario } from './use-cases/excluir-usuario'

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

  // --------------------------- Documentação (Swagger) -----------------------
  // Aqui a API publica o próprio contrato em /API/docs.
  //
  // O arquivo docs/openapi.yaml é a fonte da verdade: o Swagger UI só lê esse
  // arquivo e desenha a tela. Não geramos o contrato a partir das rotas para
  // não ter dois lugares diferentes dizendo a mesma coisa.
  //
  // `__dirname` aponta para src/ em desenvolvimento e para dist/ no build.
  // Nos dois casos, ".." cai na raiz do projeto, onde fica a pasta docs/.
  const caminhoDoOpenApi = path.join(__dirname, '..', 'docs', 'openapi.yaml')

  app.register(swagger, {
    mode: 'static',
    specification: {
      path: caminhoDoOpenApi,
      baseDir: path.dirname(caminhoDoOpenApi),
    },
  })

  app.register(swaggerUi, {
    routePrefix: '/API/docs',
    uiConfig: {
      docExpansion: 'list', // mostra a lista de rotas já aberta
      deepLinking: true, // cada rota tem um link próprio
      persistAuthorization: true, // não perde o token ao recarregar
    },
    // Em produção a API usa o próprio domínio + /API, então o seletor de
    // servidores do Swagger não acrescenta nada. Escondemos só nesse domínio;
    // no localhost ele continua aparecendo para quem está desenvolvendo.
    theme: {
      js: [
        {
          filename: 'ocultar-servidores-em-producao.js',
          content: `
            if (window.location.hostname === 'agendadeconsultas.v6.rocks') {
              const estilo = document.createElement('style')
              estilo.textContent = '.swagger-ui .scheme-container { display: none; }'
              document.head.appendChild(estilo)
            }
          `,
        },
      ],
    },
  })

  // ------------------------- Observabilidade -------------------------------
  const registro = criarRegistroDeMetricas()
  const metricas = criarMetricas(registro)

  // Rotas de infraestrutura não entram nas métricas nem nos logs de acesso:
  // o healthcheck do Coolify bate a cada 30s e poluiria tudo.
  const rotasIgnoradas = new Set([
    '/',
    '/API',
    '/health',
    '/API/health',
    '/metrics',
    '/API/metrics',
  ])

  app.addHook('onResponse', async (requisicao, resposta) => {
    const rota = requisicao.routeOptions.url ?? 'desconhecida'
    // A documentação carrega vários arquivos estáticos (JS, CSS, imagem).
    // Ignoramos tudo em /API/docs para não poluir as métricas de negócio.
    if (rota.startsWith('/API/docs')) return
    if (rota.startsWith('/docs')) return
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
  // Esta função registra /health e /metrics. Ela é chamada duas vezes:
  // na raiz (para o Coolify) e dentro de /API (para ficar junto do contrato).
  const registrarInfraestrutura = (instancia: FastifyInstance): void => {
    instancia.get('/health', async (requisicao, resposta) => {
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

    instancia.get('/metrics', async (_requisicao, resposta) => {
      resposta.type(registro.contentType)
      return registro.metrics()
    })
  }

  registrarInfraestrutura(app)

  // --------------------------- Tela de demonstração ------------------------
  // A página é um único arquivo HTML (public/index.html) com CSS e JavaScript
  // simples. Ela chama a API em /API/* usando o mesmo domínio.
  const paginaInicial = readFileSync(
    path.join(__dirname, '..', 'public', 'index.html'),
    'utf8',
  )

  app.get('/', async (_requisicao, resposta) => {
    return resposta.type('text/html; charset=utf-8').send(paginaInicial)
  })

  // Quem já conhece /docs continua funcionando: redireciona para o novo local.
  app.get('/docs', async (_requisicao, resposta) => {
    return resposta.redirect('/API/docs')
  })

  // Informações da API em JSON (útil para conferir o prefixo rapidamente).
  app.get('/API', async () => ({
    nome: 'API de Empréstimos de Biblioteca',
    nivel: 'Projeto B — Full Cycle',
    documentacao: '/API/docs',
    tela: '/',
    rotas: [
      'GET /API/health',
      'GET /API/metrics',
      'GET /API/docs',
      'POST /API/livros',
      'GET /API/livros',
      'PUT /API/livros/:id',
      'DELETE /API/livros/:id',
      'POST /API/usuarios',
      'GET /API/usuarios',
      'GET /API/usuarios/:id',
      'PUT /API/usuarios/:id',
      'DELETE /API/usuarios/:id',
      'POST /API/emprestimos',
      'GET /API/emprestimos',
      'PATCH /API/emprestimos/:id/devolucao',
      'GET /API/emprestimos/atrasados',
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

  // Casos de uso de manutenção dos cadastros (editar/excluir).
  const atualizarLivro = new AtualizarLivro(livros)
  const excluirLivro = new ExcluirLivro(livros)
  const atualizarUsuario = new AtualizarUsuario(usuarios)
  const excluirUsuario = new ExcluirUsuario(usuarios)

  // O tratamento de erro precisa ser registrado ANTES das rotas para que as
  // rotas dentro de /API herdem o mesmo formato de resposta.
  registrarTratamentoDeErros(app)

  // ------------------------------- Rotas -----------------------------------
  // Tudo que é API fica debaixo de /API. O prefixo é aplicado pelo Fastify,
  // então os arquivos de rota continuam declarando caminhos curtos
  // ("/livros", "/emprestimos").
  app.register(
    async (api) => {
      registrarInfraestrutura(api)
      registrarRotasDeLivros(api, { livros, atualizarLivro, excluirLivro })
      registrarRotasDeUsuarios(api, {
        usuarios,
        atualizarUsuario,
        excluirUsuario,
      })
      registrarRotasDeEmprestimos(api, {
        emprestarLivro,
        devolverEmprestimo,
        emprestimos,
        relogio,
        metricas,
      })
    },
    { prefix: '/API' },
  )

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
