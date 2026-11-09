import { defineConfig } from 'vitest/config'

/**
 * Configuração do Vitest (nosso runner de testes).
 *
 * Dois grupos de teste:
 *  - tests/unit        -> não tocam no banco, rodam em milissegundos
 *  - tests/integration -> usam o PostgreSQL real do docker-compose
 *
 * O coverage é medido só em src/domain e src/use-cases, que é onde ficam as
 * regras de negócio. Fazemos isso de propósito: é o número que realmente
 * importa para provar que as regras estão testadas.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    fileParallelism: false, // os testes de integração compartilham o mesmo banco
    testTimeout: 20_000,
    hookTimeout: 30_000,
    env: {
      NODE_ENV: 'test',
      LOG_LEVEL: 'silent',
      DATABASE_URL:
        process.env.DATABASE_URL ??
        'postgresql://postgres:postgres@localhost:5432/biblioteca?schema=public',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/domain/**/*.ts', 'src/use-cases/**/*.ts'],
      // Mínimo declarado no próprio projeto (exigência do Módulo 2).
      thresholds: {
        statements: 90,
        branches: 85,
        functions: 90,
        lines: 90,
      },
    },
  },
})
