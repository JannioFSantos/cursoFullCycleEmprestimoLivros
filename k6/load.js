import http from 'k6/http'
import { check } from 'k6'

/**
 * TESTE DE CARGA (k6) — mede o p95 sob concorrência.
 *
 * Dois cenários simultâneos:
 *  - leituras: 20 VUs lendo GET /livros (consulta com contagem de ativos)
 *  - escritas: até 10 VUs criando empréstimos (passa pelo FOR UPDATE)
 *
 * Por que separar? Porque o gargalo de leitura (consulta) é diferente do
 * gargalo de escrita (lock). Medir os dois juntos esconde qual está ruim.
 *
 * Rodar:
 *   k6 run k6/load.js
 *   k6 run -e BASE_URL=https://sua-api.exemplo.com k6/load.js
 *
 * Observação sobre 409: empréstimo recusado por regra de negócio NÃO é falha
 * técnica. Por isso o cenário de escrita não usa o threshold http_req_failed;
 * ele mede latência (que é o objetivo) e um check aceita 201 ou 409.
 */
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000'
const CABECALHOS = { 'Content-Type': 'application/json' }

const QUANTIDADE_DE_USUARIOS = 300

export const options = {
  scenarios: {
    leituras: {
      executor: 'constant-vus',
      vus: 20,
      duration: '1m',
      exec: 'lerLivros',
      tags: { cenario: 'leituras' },
    },
    escritas: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 10 },
        { duration: '40s', target: 10 },
        { duration: '5s', target: 0 },
      ],
      exec: 'criarEmprestimo',
      tags: { cenario: 'escritas' },
    },
  },
  thresholds: {
    // SLO declarado no README. Se estourar, o k6 termina com código != 0.
    'http_req_duration{cenario:leituras}': ['p(95)<300'],
    'http_req_duration{cenario:escritas}': ['p(95)<500'],
    'http_req_failed{cenario:leituras}': ['rate<0.01'],
    checks: ['rate>0.95'],
  },
}

/** Cria o cenário: 1 livro com muitos exemplares e vários usuários. */
export function setup() {
  const sufixo = Date.now()

  const livro = http.post(
    `${BASE_URL}/livros`,
    JSON.stringify({
      titulo: 'Livro do teste de carga',
      autor: 'k6',
      isbn: `carga-${sufixo}`,
      exemplaresTotal: 5000,
    }),
    { headers: CABECALHOS },
  )

  const usuarios = []

  for (let indice = 0; indice < QUANTIDADE_DE_USUARIOS; indice += 1) {
    const resposta = http.post(
      `${BASE_URL}/usuarios`,
      JSON.stringify({
        nome: `Usuário de carga ${indice}`,
        email: `carga-${sufixo}-${indice}@exemplo.com`,
      }),
      { headers: CABECALHOS },
    )

    usuarios.push(resposta.json('id'))
  }

  return { livroId: livro.json('id'), usuarios }
}

export function lerLivros() {
  const resposta = http.get(`${BASE_URL}/livros`, {
    tags: { operacao: 'listar_livros' },
  })

  check(resposta, {
    'GET /livros responde 200': (res) => res.status === 200,
  })
}

export function criarEmprestimo(dados) {
  // Cada iteração sorteia um usuário. Depois de 3 empréstimos ativos, aquele
  // usuário recebe 409 — o que é esperado e não invalida o teste.
  const usuarioId = dados.usuarios[Math.floor(Math.random() * dados.usuarios.length)]

  const resposta = http.post(
    `${BASE_URL}/emprestimos`,
    JSON.stringify({ livroId: dados.livroId, usuarioId }),
    { headers: CABECALHOS, tags: { operacao: 'criar_emprestimo' } },
  )

  check(resposta, {
    'POST /emprestimos responde 201 (criou) ou 409 (regra)': (res) =>
      res.status === 201 || res.status === 409,
  })
}
