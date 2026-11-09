import { collectDefaultMetrics, Counter, Histogram, Registry } from 'prom-client'

/**
 * Métricas no formato Prometheus.
 *
 * Escolhemos duas métricas enxutas, que respondem às perguntas do dia a dia:
 *  1. "a API está lenta?"        -> histograma de duração por rota
 *  2. "quantos empréstimos saem?" -> contador de criados x recusados
 *
 * O Registry é criado POR APLICAÇÃO (e não global) para que os testes possam
 * montar várias instâncias sem o erro "metric already registered".
 */
export interface Metricas {
  duracaoHttp: Histogram<'metodo' | 'rota' | 'status'>
  emprestimos: Counter<'resultado'>
}

export function criarRegistroDeMetricas(): Registry {
  const registro = new Registry()

  // Métricas de processo (CPU, memória, event loop...). Vêm de graça do
  // prom-client e ajudam a explicar comportamentos estranhos sob carga.
  collectDefaultMetrics({ register: registro })

  return registro
}

export function criarMetricas(registro: Registry): Metricas {
  const duracaoHttp = new Histogram({
    name: 'http_request_duration_seconds',
    help: 'Duração das requisições HTTP em segundos',
    labelNames: ['metodo', 'rota', 'status'] as const,
    // Buckets escolhidos em volta do nosso SLO (p95 < 300 ms).
    buckets: [0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5],
    registers: [registro],
  })

  const emprestimos = new Counter({
    name: 'emprestimos_total',
    help: 'Total de tentativas de empréstimo, separadas por resultado',
    labelNames: ['resultado'] as const,
    registers: [registro],
  })

  return { duracaoHttp, emprestimos }
}
