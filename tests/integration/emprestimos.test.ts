import type { FastifyInstance } from 'fastify'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { criarApp } from '../../src/app'
import { prisma } from '../../src/infra/prisma/client'

/**
 * Teste de INTEGRAÇÃO (o obrigatório do Projeto B, e um pouco além).
 *
 * Diferente dos unitários, aqui nada é fake: a API inteira roda com o
 * PostgreSQL real, passando por HTTP -> rota -> caso de uso -> Prisma -> banco.
 *
 * Usamos `app.inject()` em vez de abrir uma porta: é o mesmo caminho de uma
 * requisição real, só que sem rede. É o equivalente ao Supertest no Fastify.
 *
 * Repare que todas as rotas de negócio começam com /API. É o mesmo prefixo
 * que a produção usa (https://agendadeconsultas.v6.rocks/API).
 *
 * Pré-requisito: `docker compose up -d db` e `npm run db:deploy`.
 * ATENÇÃO: este teste LIMPA as tabelas antes de cada caso. Nunca rode contra
 * um banco com dados que você queira manter.
 */

let app: FastifyInstance

// Relógio controlável: mudando `agora`, simulamos a passagem dos dias.
let agora: Date
const relogio = { agora: () => agora }

let sequencia = 0

function proximoIsbn(): string {
  sequencia += 1
  return `978000000${String(sequencia).padStart(4, '0')}`
}

beforeAll(async () => {
  try {
    await prisma.$queryRaw`SELECT 1`
  } catch {
    throw new Error(
      'Banco indisponível. Suba com "docker compose up -d db" e rode "npm run db:deploy".',
    )
  }

  app = criarApp({ prisma, relogio })
  await app.ready()
})

beforeEach(async () => {
  // Ordem importa por causa das chaves estrangeiras.
  await prisma.emprestimo.deleteMany()
  await prisma.livro.deleteMany()
  await prisma.usuario.deleteMany()

  agora = new Date('2026-01-05T12:00:00.000Z')
})

afterAll(async () => {
  if (app) await app.close()
  await prisma.$disconnect()
})

async function criarLivro(exemplaresTotal: number): Promise<{ id: string; titulo: string }> {
  const resposta = await app.inject({
    method: 'POST',
    url: '/API/livros',
    payload: {
      titulo: `Livro ${sequencia}`,
      autor: 'Autor de teste',
      isbn: proximoIsbn(),
      exemplaresTotal,
    },
  })

  expect(resposta.statusCode).toBe(201)
  return resposta.json()
}

async function criarUsuario(): Promise<{ id: string; nome: string }> {
  sequencia += 1
  const resposta = await app.inject({
    method: 'POST',
    url: '/API/usuarios',
    payload: {
      nome: `Usuário ${sequencia}`,
      email: `usuario-${sequencia}@exemplo.com`,
    },
  })

  expect(resposta.statusCode).toBe(201)
  return resposta.json()
}

async function emprestar(livroId: string, usuarioId: string) {
  return app.inject({
    method: 'POST',
    url: '/API/emprestimos',
    payload: { livroId, usuarioId },
  })
}

describe('API de empréstimos (integração)', () => {
  it('serve a tela de demonstração na raiz', async () => {
    const resposta = await app.inject({ method: 'GET', url: '/' })

    expect(resposta.statusCode).toBe(200)
    expect(resposta.headers['content-type']).toContain('text/html')
    expect(resposta.body).toContain('Biblioteca')
    expect(resposta.body).toContain('/API')
  })

  it('responde 200 no healthcheck quando o banco está acessível', async () => {
    // O healthcheck fica na raiz porque é o endereço que o Coolify usa.
    const raiz = await app.inject({ method: 'GET', url: '/health' })
    expect(raiz.statusCode).toBe(200)
    expect(raiz.json()).toMatchObject({ status: 'ok' })

    // E também dentro de /API, junto do resto do contrato.
    const dentroDaApi = await app.inject({ method: 'GET', url: '/API/health' })
    expect(dentroDaApi.statusCode).toBe(200)
  })

  it('publica a documentação Swagger em /API/docs', async () => {
    const pagina = await app.inject({ method: 'GET', url: '/API/docs/' })

    expect(pagina.statusCode).toBe(200)
    expect(pagina.body.toLowerCase()).toContain('swagger')

    // /API/docs/json é o mesmo contrato, em JSON, que o Swagger UI carrega.
    const contrato = await app.inject({ method: 'GET', url: '/API/docs/json' })

    expect(contrato.statusCode).toBe(200)
    expect(contrato.json()).toMatchObject({ openapi: '3.1.0' })

    // Quem digitava /docs continua chegando na documentação nova.
    const antigo = await app.inject({ method: 'GET', url: '/docs' })
    expect(antigo.statusCode).toBe(302)
    expect(antigo.headers.location).toBe('/API/docs')
  })

  it('empresta um livro e calcula a data prevista', async () => {
    const livro = await criarLivro(1)
    const usuario = await criarUsuario()

    const resposta = await emprestar(livro.id, usuario.id)

    expect(resposta.statusCode).toBe(201)
    expect(resposta.json()).toMatchObject({
      livroId: livro.id,
      usuarioId: usuario.id,
      status: 'ATIVO',
      dataPrevista: '2026-01-19T00:00:00.000Z',
    })
  })

  it('lista usuários e empréstimos detalhados para a tela', async () => {
    const livro = await criarLivro(1)
    const usuario = await criarUsuario()
    await emprestar(livro.id, usuario.id)

    const usuarios = await app.inject({ method: 'GET', url: '/API/usuarios' })
    expect(usuarios.statusCode).toBe(200)
    expect(usuarios.json().itens).toHaveLength(1)
    expect(usuarios.json().itens[0]).toMatchObject({
      id: usuario.id,
      nome: usuario.nome,
    })

    const emprestimos = await app.inject({ method: 'GET', url: '/API/emprestimos' })
    expect(emprestimos.statusCode).toBe(200)
    expect(emprestimos.json().itens).toHaveLength(1)
    expect(emprestimos.json().itens[0]).toMatchObject({
      status: 'ATIVO',
      livro: { id: livro.id },
      usuario: { id: usuario.id, nome: usuario.nome },
    })
  })

  it('recusa o segundo empréstimo quando só existe um exemplar', async () => {
    const livro = await criarLivro(1)
    const primeiro = await criarUsuario()
    const segundo = await criarUsuario()

    expect((await emprestar(livro.id, primeiro.id)).statusCode).toBe(201)

    const resposta = await emprestar(livro.id, segundo.id)

    expect(resposta.statusCode).toBe(409)
    expect(resposta.json()).toMatchObject({
      erro: { codigo: 'LIVRO_INDISPONIVEL' },
    })
  })

  it('devolve o livro e permite um novo empréstimo', async () => {
    const livro = await criarLivro(1)
    const usuario = await criarUsuario()

    const criado = await emprestar(livro.id, usuario.id)
    const emprestimoId = criado.json().id as string

    const devolucao = await app.inject({
      method: 'PATCH',
      url: `/API/emprestimos/${emprestimoId}/devolucao`,
    })

    expect(devolucao.statusCode).toBe(200)
    expect(devolucao.json()).toMatchObject({ status: 'DEVOLVIDO' })

    const outroUsuario = await criarUsuario()
    expect((await emprestar(livro.id, outroUsuario.id)).statusCode).toBe(201)
  })

  it('bloqueia usuário em atraso e lista o empréstimo em /atrasados', async () => {
    const livro = await criarLivro(1)
    const outroLivro = await criarLivro(1)
    const usuario = await criarUsuario()

    await emprestar(livro.id, usuario.id)

    // "Viajamos" 30 dias no tempo: o empréstimo de 14 dias está atrasado.
    agora = new Date('2026-02-04T12:00:00.000Z')

    const tentativa = await emprestar(outroLivro.id, usuario.id)
    expect(tentativa.statusCode).toBe(409)
    expect(tentativa.json()).toMatchObject({
      erro: { codigo: 'USUARIO_COM_ATRASO' },
    })

    const atrasados = await app.inject({
      method: 'GET',
      url: '/API/emprestimos/atrasados',
    })

    expect(atrasados.statusCode).toBe(200)
    expect(atrasados.json().itens).toHaveLength(1)
    expect(atrasados.json().itens[0]).toMatchObject({
      usuario: { id: usuario.id },
      livro: { id: livro.id },
    })
  })

  it('recusa o quarto empréstimo ativo do mesmo usuário', async () => {
    const usuario = await criarUsuario()

    for (let indice = 0; indice < 3; indice += 1) {
      const livro = await criarLivro(1)
      expect((await emprestar(livro.id, usuario.id)).statusCode).toBe(201)
    }

    const quartoLivro = await criarLivro(1)
    const resposta = await emprestar(quartoLivro.id, usuario.id)

    expect(resposta.statusCode).toBe(409)
    expect(resposta.json()).toMatchObject({ erro: { codigo: 'LIMITE_ATINGIDO' } })
  })

  it('retorna 404 para livro inexistente', async () => {
    const usuario = await criarUsuario()

    const resposta = await emprestar(
      '00000000-0000-4000-8000-000000000000',
      usuario.id,
    )

    expect(resposta.statusCode).toBe(404)
    expect(resposta.json()).toMatchObject({
      erro: { codigo: 'LIVRO_NAO_ENCONTRADO' },
    })
  })

  it('retorna 400 com detalhes quando o corpo é inválido', async () => {
    const resposta = await app.inject({
      method: 'POST',
      url: '/API/emprestimos',
      payload: { livroId: 'nao-e-uuid', usuarioId: 'tambem-nao' },
    })

    expect(resposta.statusCode).toBe(400)
    expect(resposta.json()).toMatchObject({ erro: { codigo: 'DADOS_INVALIDOS' } })
  })

  it('retorna 409 ao cadastrar ISBN repetido', async () => {
    const isbn = '9780000009999'
    const payload = {
      titulo: 'Livro com ISBN fixo',
      autor: 'Autor de teste',
      isbn,
      exemplaresTotal: 1,
    }

    const primeiro = await app.inject({ method: 'POST', url: '/API/livros', payload })
    expect(primeiro.statusCode).toBe(201)

    // O Prisma devolve P2002 e o error handler traduz para 409 padronizado.
    const repetido = await app.inject({ method: 'POST', url: '/API/livros', payload })

    expect(repetido.statusCode).toBe(409)
    expect(repetido.json()).toMatchObject({
      erro: { codigo: 'VALOR_JA_CADASTRADO' },
    })
  })

  it('edita um livro com PUT', async () => {
    const livro = await criarLivro(2)

    const resposta = await app.inject({
      method: 'PUT',
      url: `/API/livros/${livro.id}`,
      payload: {
        titulo: 'Livro editado',
        autor: 'Autor editado',
        isbn: '9780000007777',
        exemplaresTotal: 4,
      },
    })

    expect(resposta.statusCode).toBe(200)
    expect(resposta.json()).toMatchObject({
      id: livro.id,
      titulo: 'Livro editado',
      autor: 'Autor editado',
      isbn: '9780000007777',
      exemplaresTotal: 4,
    })
  })

  it('recusa reduzir exemplares abaixo dos empréstimos ativos', async () => {
    const livro = await criarLivro(2)
    const primeiro = await criarUsuario()
    const segundo = await criarUsuario()

    expect((await emprestar(livro.id, primeiro.id)).statusCode).toBe(201)
    expect((await emprestar(livro.id, segundo.id)).statusCode).toBe(201)

    const resposta = await app.inject({
      method: 'PUT',
      url: `/API/livros/${livro.id}`,
      payload: {
        titulo: livro.titulo,
        autor: 'Autor de teste',
        isbn: '9780000008888',
        exemplaresTotal: 1,
      },
    })

    expect(resposta.statusCode).toBe(409)
    expect(resposta.json()).toMatchObject({
      erro: { codigo: 'EXEMPLARES_ABAIXO_DOS_EMPRESTIMOS' },
    })
  })

  it('exclui livro sem empréstimos e recusa livro com histórico', async () => {
    const semEmprestimo = await criarLivro(1)

    const excluido = await app.inject({
      method: 'DELETE',
      url: `/API/livros/${semEmprestimo.id}`,
    })
    expect(excluido.statusCode).toBe(204)

    const lista = await app.inject({ method: 'GET', url: '/API/livros' })
    expect(lista.json().itens.map((item: { id: string }) => item.id)).not.toContain(
      semEmprestimo.id,
    )

    const comEmprestimo = await criarLivro(1)
    const usuario = await criarUsuario()
    await emprestar(comEmprestimo.id, usuario.id)

    const recusado = await app.inject({
      method: 'DELETE',
      url: `/API/livros/${comEmprestimo.id}`,
    })

    expect(recusado.statusCode).toBe(409)
    expect(recusado.json()).toMatchObject({
      erro: { codigo: 'LIVRO_COM_EMPRESTIMOS' },
    })
  })

  it('edita um usuário com PUT', async () => {
    const usuario = await criarUsuario()

    const resposta = await app.inject({
      method: 'PUT',
      url: `/API/usuarios/${usuario.id}`,
      payload: { nome: 'Nome editado', email: 'editado@exemplo.com' },
    })

    expect(resposta.statusCode).toBe(200)
    expect(resposta.json()).toMatchObject({
      id: usuario.id,
      nome: 'Nome editado',
      email: 'editado@exemplo.com',
    })
  })

  it('exclui usuário sem empréstimos e recusa usuário com histórico', async () => {
    const semEmprestimo = await criarUsuario()

    const excluido = await app.inject({
      method: 'DELETE',
      url: `/API/usuarios/${semEmprestimo.id}`,
    })
    expect(excluido.statusCode).toBe(204)

    const lista = await app.inject({ method: 'GET', url: '/API/usuarios' })
    expect(lista.json().itens.map((item: { id: string }) => item.id)).not.toContain(
      semEmprestimo.id,
    )

    const livro = await criarLivro(1)
    const comEmprestimo = await criarUsuario()
    await emprestar(livro.id, comEmprestimo.id)

    const recusado = await app.inject({
      method: 'DELETE',
      url: `/API/usuarios/${comEmprestimo.id}`,
    })

    expect(recusado.statusCode).toBe(409)
    expect(recusado.json()).toMatchObject({
      erro: { codigo: 'USUARIO_COM_EMPRESTIMOS' },
    })
  })

  it('retorna 404 ao editar ou excluir recurso inexistente', async () => {
    const idInexistente = '00000000-0000-4000-8000-000000000000'

    const editarLivro = await app.inject({
      method: 'PUT',
      url: `/API/livros/${idInexistente}`,
      payload: {
        titulo: 'Livro',
        autor: 'Autor',
        isbn: '9780000006666',
        exemplaresTotal: 1,
      },
    })
    expect(editarLivro.statusCode).toBe(404)

    const excluirLivro = await app.inject({
      method: 'DELETE',
      url: `/API/livros/${idInexistente}`,
    })
    expect(excluirLivro.statusCode).toBe(404)

    const editarUsuario = await app.inject({
      method: 'PUT',
      url: `/API/usuarios/${idInexistente}`,
      payload: { nome: 'Nome', email: 'nome@exemplo.com' },
    })
    expect(editarUsuario.statusCode).toBe(404)

    const excluirUsuario = await app.inject({
      method: 'DELETE',
      url: `/API/usuarios/${idInexistente}`,
    })
    expect(excluirUsuario.statusCode).toBe(404)
  })
})
