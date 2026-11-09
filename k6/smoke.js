import http from 'k6/http'
import { check, fail } from 'k6'

/**
 * SMOKE TEST (k6) — valida o fluxo principal uma única vez.
 *
 * O que ele prova: a API sobe, aceita os dados, empresta, devolve e lista.
 * Se este teste falhar, não adianta rodar o teste de carga.
 *
 * Rodar:
 *   docker compose up -d
 *   k6 run k6/smoke.js
 *   # ou apontando para o Coolify (repare no /API no final):
 *   k6 run -e BASE_URL=https://agendadeconsultas.v6.rocks/API k6/smoke.js
 */
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000/API'
const CABECALHOS = { 'Content-Type': 'application/json' }

export const options = {
  // 1 usuário virtual, 1 iteração: smoke test de verdade é curto e barato.
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
    // SLO do projeto: p95 abaixo de 300 ms.
    http_req_duration: ['p(95)<300'],
  },
}

/** Executa UMA vez antes das iterações e devolve dados para o teste. */
export function setup() {
  const sufixo = Date.now()

  const livro = http.post(
    `${BASE_URL}/livros`,
    JSON.stringify({
      titulo: 'Livro do smoke test',
      autor: 'k6',
      isbn: `smoke-${sufixo}`,
      exemplaresTotal: 5,
    }),
    { headers: CABECALHOS },
  )

  if (livro.status !== 201) {
    fail(`não foi possível criar o livro: ${livro.status} ${livro.body}`)
  }

  const usuario = http.post(
    `${BASE_URL}/usuarios`,
    JSON.stringify({
      nome: 'Usuário do smoke test',
      email: `smoke-${sufixo}@exemplo.com`,
    }),
    { headers: CABECALHOS },
  )

  if (usuario.status !== 201) {
    fail(`não foi possível criar o usuário: ${usuario.status} ${usuario.body}`)
  }

  return {
    livroId: livro.json('id'),
    usuarioId: usuario.json('id'),
  }
}

export default function (dados) {
  // 1) Emprestar
  const emprestimo = http.post(
    `${BASE_URL}/emprestimos`,
    JSON.stringify({ livroId: dados.livroId, usuarioId: dados.usuarioId }),
    { headers: CABECALHOS, tags: { operacao: 'criar_emprestimo' } },
  )

  const criou = check(emprestimo, {
    'POST /emprestimos responde 201': (resposta) => resposta.status === 201,
    'empréstimo nasce com status ATIVO': (resposta) =>
      resposta.json('status') === 'ATIVO',
  })

  if (!criou) return

  const emprestimoId = emprestimo.json('id')

  // 2) Devolver
  const devolucao = http.patch(
    `${BASE_URL}/emprestimos/${emprestimoId}/devolucao`,
    null,
    { tags: { operacao: 'devolver_emprestimo' } },
  )

  check(devolucao, {
    'PATCH /devolucao responde 200': (resposta) => resposta.status === 200,
    'empréstimo fica DEVOLVIDO': (resposta) => resposta.json('status') === 'DEVOLVIDO',
  })

  // 3) Listar atrasados (deve estar vazio)
  const atrasados = http.get(`${BASE_URL}/emprestimos/atrasados`, {
    tags: { operacao: 'listar_atrasados' },
  })

  check(atrasados, {
    'GET /atrasados responde 200': (resposta) => resposta.status === 200,
  })
}
