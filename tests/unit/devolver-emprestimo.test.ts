import { beforeEach, describe, expect, it } from 'vitest'
import { DevolverEmprestimo } from '../../src/use-cases/devolver-emprestimo'
import { EmprestarLivro } from '../../src/use-cases/emprestar-livro'
import {
  criarLivroFake,
  criarUsuarioFake,
  EmprestimoRepositorioFake,
  LivroRepositorioFake,
  UsuarioRepositorioFake,
} from './fakes'

describe('DevolverEmprestimo', () => {
  let livros: LivroRepositorioFake
  let usuarios: UsuarioRepositorioFake
  let emprestimos: EmprestimoRepositorioFake

  const agora = new Date('2026-01-10T09:00:00.000Z')

  beforeEach(() => {
    livros = new LivroRepositorioFake()
    usuarios = new UsuarioRepositorioFake()
    emprestimos = new EmprestimoRepositorioFake(livros, usuarios)
  })

  async function criarEmprestimo() {
    const livro = criarLivroFake({ exemplaresTotal: 1 })
    const usuario = criarUsuarioFake()
    livros.livros.push(livro)
    usuarios.usuarios.push(usuario)

    const emprestar = new EmprestarLivro(
      livros,
      usuarios,
      emprestimos,
      { agora: () => new Date('2026-01-05T12:00:00.000Z') },
      14,
      3,
    )

    return emprestar.executar({ livroId: livro.id, usuarioId: usuario.id })
  }

  it('marca o empréstimo como DEVOLVIDO com a data atual', async () => {
    const emprestimo = await criarEmprestimo()
    const devolver = new DevolverEmprestimo(emprestimos, { agora: () => agora })

    const devolvido = await devolver.executar(emprestimo.id)

    expect(devolvido.status).toBe('DEVOLVIDO')
    expect(devolvido.dataDevolucao?.toISOString()).toBe(agora.toISOString())
  })

  it('retorna 404 quando o empréstimo não existe', async () => {
    const devolver = new DevolverEmprestimo(emprestimos)

    await expect(devolver.executar('inexistente')).rejects.toMatchObject({
      codigo: 'EMPRESTIMO_NAO_ENCONTRADO',
      statusCode: 404,
    })
  })

  it('recusa devolver o mesmo empréstimo duas vezes', async () => {
    const emprestimo = await criarEmprestimo()
    const devolver = new DevolverEmprestimo(emprestimos, { agora: () => agora })

    await devolver.executar(emprestimo.id)

    await expect(devolver.executar(emprestimo.id)).rejects.toMatchObject({
      codigo: 'EMPRESTIMO_JA_DEVOLVIDO',
      statusCode: 409,
    })
  })
})
