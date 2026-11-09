// Carrega o arquivo .env para dentro de process.env ANTES de qualquer leitura.
// Em produção (Coolify) as variáveis vêm do painel, então o .env nem existe:
// o dotenv simplesmente não encontra o arquivo e segue em frente.
import 'dotenv/config'

import { z } from 'zod'

/**
 * Aqui validamos as variáveis de ambiente na inicialização.
 *
 * Por que isso importa: se a aplicação sobe sem DATABASE_URL, ela falha com um
 * erro confuso só na primeira requisição. Validando agora, o container morre
 * imediatamente com uma mensagem clara — o que é muito melhor em produção.
 */
const esquemaDeAmbiente = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),
  // 0.0.0.0 é obrigatório em container: sem isso o Fastify escuta só no
  // loopback e o Coolify/Docker não conseguem acessar a API.
  HOST: z.string().min(1).default('0.0.0.0'),
  LOG_LEVEL: z
    .enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent'])
    .default('info'),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL é obrigatória'),
  PRAZO_DIAS: z.coerce.number().int().positive().default(14),
  LIMITE_EMPRESTIMOS: z.coerce.number().int().positive().default(3),
})

const resultado = esquemaDeAmbiente.safeParse(process.env)

if (!resultado.success) {
  // Mensagem legível para quem está subindo o projeto pela primeira vez.
  console.error('❌ Variáveis de ambiente inválidas:')
  console.error(JSON.stringify(resultado.error.flatten().fieldErrors, null, 2))
  console.error('💡 Copie o .env.example para .env e tente novamente.')
  process.exit(1)
}

/**
 * Objeto único, já validado e tipado, usado pelo resto da aplicação.
 * Nenhum outro arquivo lê `process.env` diretamente: assim existe um só lugar
 * para descobrir "quais configurações esse projeto precisa".
 */
export const env = resultado.data

export type Ambiente = typeof env
