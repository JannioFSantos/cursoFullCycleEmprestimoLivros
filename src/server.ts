// Ponto de entrada da aplicação em produção (e em desenvolvimento).
// Este arquivo é o único que conhece a porta e o ciclo de vida do processo.
import { criarApp } from './app'
import { env } from './config/env'
import { prisma } from './infra/prisma/client'

async function iniciar(): Promise<void> {
  const app = criarApp({
    prisma,
    prazoEmDias: env.PRAZO_DIAS,
    limiteDeEmprestimos: env.LIMITE_EMPRESTIMOS,
  })

  try {
    // HOST = 0.0.0.0 é essencial em container (Coolify/Docker).
    await app.listen({ port: env.PORT, host: env.HOST })
    app.log.info(
      { porta: env.PORT, ambiente: env.NODE_ENV },
      'api_iniciada',
    )
  } catch (erro) {
    app.log.error({ err: erro }, 'falha_ao_iniciar_api')
    process.exit(1)
  }

  /**
   * Encerramento gracioso.
   *
   * Quando o Coolify faz um novo deploy, ele manda SIGTERM. Se sairmos na
   * hora, requisições em andamento são cortadas. Fechamos o servidor (que
   * espera as requisições terminarem) e só depois o pool do banco.
   */
  const encerrar = async (sinal: string): Promise<void> => {
    app.log.info({ sinal }, 'encerrando_api')
    try {
      await app.close()
      await prisma.$disconnect()
      process.exit(0)
    } catch (erro) {
      app.log.error({ err: erro }, 'falha_ao_encerrar_api')
      process.exit(1)
    }
  }

  process.on('SIGTERM', () => void encerrar('SIGTERM'))
  process.on('SIGINT', () => void encerrar('SIGINT'))
}

void iniciar()
