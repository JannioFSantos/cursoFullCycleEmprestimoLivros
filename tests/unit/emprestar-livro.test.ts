import { beforeEach, describe, expect, it } from 'vitest'
import { EmprestarLivro } from '../../src/use-cases/emprestar-livro'
import type { ErroDeDominio } from '../../src/domain/erros'
import {
  criarLivroFake,
  criarUsuarioFake,
  EmprestimoRepositorioFake,
  LivroRepositorioFake,
  UsuarioRepositorioFake,
} from './fakes'

/**
 * Testes do caso de uso "emprestar livro".
 *
 * Aqui os três repositórios são fakes em memória. O que estamos provando é a
 * orquestração: buscar livro/usuário, calcular datas, delegar a validação e
 * devolver o empréstimo criado — inclusive os caminhos de erro.
 */

describe('EmprestarLivro', () => {
  let livros: LivroRepositorioFake
  let usuarios: UsuarioRepositorioFake
  let emprestimos: EmprestimoRepositorioFake
  let casoDeUso: EmprestarLivro

  const agora = new Date('2026-01-05T12:00:00.000Z')

  beforeEach(() => {
    livros = new LivroRepositorioFake()
    usuarios = new UsuarioRepositorioFake()
    emprestimos = new EmprestimoRepositorioFake(livros, usuarios)

    casoDeUso = new EmprestarLivro(
      livros,
      usuarios,
      emprestimos,
      { agora: () => agora },
      14,
      3,
    )
  })

  async function prepararCenario(exemplaresTotal = 1) {
    const livro = criarLivroFake({ exemplaresTotal })
    const usuario = criarUsuarioFake()
    livros.livros.push(livro)
    usuarios.usuarios.push(usuario)
    return { livro, usuario }
  }

  it('cria o empréstimo com prazo de 14 dias', async () => {
    const { livro, usuario } = await prepararCenario()

    const emprestimo = await casoDeUso.executar({
      livroId: livro.id,
      usuarioId: usuario.id,
    })

    expect(emprestimo.status).toBe('ATIVO')
    expect(emprestimo.dataEmprestimo.toISOString()).toBe(agora.toISOString())
    expect(emprestimo.dataPrevista.toISOString()).toBe('2026-01-19T00:00:00.000Z')
    expect(emprestimos.emprestimos).toHaveLength(1)
  })

  it('retorna erro 404 quando o livro não existe', async () => {
    const usuario = criarUsuarioFake()
    usuarios.usuarios.push(usuario)

    await expect(
      casoDeUso.executar({ livroId: 'inexistente', usuarioId: usuario.id }),
    ).rejects.toMatchObject({ codigo: 'LIVRO_NAO_ENCONTRADO', statusCode: 404 })
  })

  it('retorna erro 404 quando o usuário não existe', async () => {
    const { livro } = await prepararCenario()

    await expect(
      casoDeUso.executar({ livroId: livro.id, usuarioId: 'inexistente' }),
    ).rejects.toMatchObject({ codigo: 'USUARIO_NAO_ENCONTRADO', statusCode: 404 })
  })

  it('recusa quando não há exemplar disponível', async () => {
    const { livro, usuario } = await prepararCenario(1)

    await casoDeUso.executar({ livroId: livro.id, usuarioId: usuario.id })

    const outroUsuario = criarUsuarioFake()
    usuarios.usuarios.push(outroUsuario)

    await expect(
      casoDeUso.executar({ livroId: livro.id, usuarioId: outroUsuario.id }),
    ).rejects.toMatchObject({ codigo: 'LIVRO_INDISPONIVEL' })
  })

  it('recusa usuário com empréstimo em atraso', async () => {
    // Primeiro empréstimo feito no passado...
    const passado = new Date('2025-12-01T12:00:00.000Z')
    const casoDeUsoNoPassado = new EmprestarLivro(
      livros,
      usuarios,
      emprestimos,
      { agora: () => passado },
      14,
      3,
    )

    const livroAntigo = criarLivroFake({ exemplaresTotal: 1 })
    livros.livros.push(livroAntigo)
    const usuario = criarUsuarioFake()
    usuarios.usuarios.push(usuario)

    await casoDeUsoNoPassado.executar({
      livroId: livroAntigo.id,
      usuarioId: usuario.id,
    })

    // ...e um novo pedido hoje, com o primeiro já vencido.
    const livroNovo = criarLivroFake({ exemplaresTotal: 1 })
    livros.livros.push(livroNovo)

    await expect(
      casoDeUso.executar({ livroId: livroNovo.id, usuarioId: usuario.id }),
    ).rejects.toMatchObject({ codigo: 'USUARIO_COM_ATRASO' })
  })

  it('recusa ao atingir 3 empréstimos ativos', async () => {
    const usuario = criarUsuarioFake()
    usuarios.usuarios.push(usuario)

    for (let indice = 0; indice < 3; indice += 1) {
      const livro = criarLivroFake({ exemplaresTotal: 1 })
      livros.livros.push(livro)
      await casoDeUso.executar({ livroId: livro.id, usuarioId: usuario.id })
    }

    const quartoLivro = criarLivroFake({ exemplaresTotal: 1 })
    livros.livros.push(quartoLivro)

    await expect(
      casoDeUso.executar({ livroId: quartoLivro.id, usuarioId: usuario.id }),
    ).rejects.toMatchObject({ codigo: 'LIMITE_ATINGIDO' })
  })

  it('o erro de negócio carrega mensagem pronta para a API', async () => {
    const { livro, usuario } = await prepararCenario(1)
    await casoDeUso.executar({ livroId: livro.id, usuarioId: usuario.id })

    const outroUsuario = criarUsuarioFake()
    usuarios.usuarios.push(outroUsuario)

    try {
      await casoDeUso.executar({ livroId: livro.id, usuarioId: outroUsuario.id })
      expect.unreachable('deveria ter lançado erro')
    } catch (erro) {
      const erroDeDominio = erro as ErroDeDominio
      expect(erroDeDominio.name).toBe('ErroDeDominio')
      expect(erroDeDominio.statusCode).toBe(409)
      expect(erroDeDominio.message).toContain('exemplar')
    }
  })
})
