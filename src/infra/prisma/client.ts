import { PrismaClient } from '@prisma/client'
import { env } from '../../config/env'

/**
 * Instância única do Prisma Client.
 *
 * Reutilizar a mesma instância evita abrir um pool de conexões novo a cada
 * requisição. No hot-reload do `npm run dev`, guardamos a instância em
 * globalThis para não estourar o limite de conexões do Postgres.
 */
const globalParaPrisma = globalThis as unknown as { prisma?: PrismaClient }

export const prisma =
  globalParaPrisma.prisma ??
  new PrismaClient({
    log: env.NODE_ENV === 'development' ? ['warn', 'error'] : ['error'],
  })

if (env.NODE_ENV !== 'production') {
  globalParaPrisma.prisma = prisma
}
