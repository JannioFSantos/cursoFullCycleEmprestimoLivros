import { beforeEach, describe, expect, it } from 'vitest'
import { AtualizarLivro } from '../../src/use-cases/atualizar-livro'
import { ExcluirLivro } from '../../src/use-cases/excluir-livro'
import { AtualizarUsuario } from '../../src/use-cases/atualizar-usuario'
import { ExcluirUsuario } from '../../src/use-cases/excluir-usuario'
import {
  criarLivroFake,
  criarUsuarioFake,
  LivroRepositorioFake,
  UsuarioRepositorioFake,
} from './fakes'

describe('Manutenção de cadastros', () => {
  let livros: LivroRepositorioFake
  let usuarios: UsuarioRepositorioFake

  beforeEach(() => {
    livros = new LivroRepositorioFake()
    usuarios = new UsuarioRepositorioFake()
  })

  describe('AtualizarLivro', () => {
    it('edita título, autor, ISBN e exemplares', async () => {
      const livro = criarLivroFake({ exemplaresTotal: 3 })
      livros.livros.push(livro)

      const atualizar = new AtualizarLivro(livros)
      const atualizado = await atualizar.executar(livro.id, {
        titulo: 'Título novo',
        autor: 'Autor novo',
        isbn: '9780000000001',
        exemplaresTotal: 5,
      })

      expect(atualizado).toMatchObject({
        id: livro.id,
        titulo: 'Título novo',
        autor: 'Autor novo',
        isbn: '9780000000001',
        exemplaresTotal: 5,
      })
    })

    it('recusa reduzir os exemplares abaixo dos empréstimos ativos', async () => {
      const livro = criarLivroFake({ exemplaresTotal: 3 })
      livros.livros.push(livro)
      livros.emprestimosAtivos = 2

      const atualizar = new AtualizarLivro(livros)

      await expect(
        atualizar.executar(livro.id, {
          titulo: livro.titulo,
          autor: livro.autor,
          isbn: livro.isbn,
          exemplaresTotal: 1,
        }),
      ).rejects.toMatchObject({
        codigo: 'EXEMPLARES_ABAIXO_DOS_EMPRESTIMOS',
        statusCode: 409,
      })
    })

    it('retorna 404 quando o livro não existe', async () => {
      const atualizar = new AtualizarLivro(livros)

      await expect(
        atualizar.executar('00000000-0000-4000-8000-000000000000', {
          titulo: 'Título',
          autor: 'Autor',
          isbn: '9780000000002',
          exemplaresTotal: 1,
        }),
      ).rejects.toMatchObject({ codigo: 'LIVRO_NAO_ENCONTRADO', statusCode: 404 })
    })
  })

  describe('ExcluirLivro', () => {
    it('exclui um livro sem empréstimos', async () => {
      const livro = criarLivroFake({ exemplaresTotal: 1 })
      livros.livros.push(livro)

      const excluir = new ExcluirLivro(livros)
      await excluir.executar(livro.id)

      expect(await livros.buscarPorId(livro.id)).toBeNull()
    })

    it('recusa excluir livro com empréstimos registrados', async () => {
      const livro = criarLivroFake({ exemplaresTotal: 1 })
      livros.livros.push(livro)
      livros.emprestimosRegistrados = 1

      const excluir = new ExcluirLivro(livros)

      await expect(excluir.executar(livro.id)).rejects.toMatchObject({
        codigo: 'LIVRO_COM_EMPRESTIMOS',
        statusCode: 409,
      })
      expect(await livros.buscarPorId(livro.id)).not.toBeNull()
    })

    it('retorna 404 quando o livro não existe', async () => {
      const excluir = new ExcluirLivro(livros)

      await expect(
        excluir.executar('00000000-0000-4000-8000-000000000000'),
      ).rejects.toMatchObject({ codigo: 'LIVRO_NAO_ENCONTRADO', statusCode: 404 })
    })
  })

  describe('AtualizarUsuario', () => {
    it('edita nome e e-mail', async () => {
      const usuario = criarUsuarioFake()
      usuarios.usuarios.push(usuario)

      const atualizar = new AtualizarUsuario(usuarios)
      const atualizado = await atualizar.executar(usuario.id, {
        nome: 'Nome novo',
        email: 'nome.novo@exemplo.com',
      })

      expect(atualizado).toMatchObject({
        id: usuario.id,
        nome: 'Nome novo',
        email: 'nome.novo@exemplo.com',
      })
    })

    it('retorna 404 quando o usuário não existe', async () => {
      const atualizar = new AtualizarUsuario(usuarios)

      await expect(
        atualizar.executar('00000000-0000-4000-8000-000000000000', {
          nome: 'Nome',
          email: 'nome@exemplo.com',
        }),
      ).rejects.toMatchObject({ codigo: 'USUARIO_NAO_ENCONTRADO', statusCode: 404 })
    })
  })

  describe('ExcluirUsuario', () => {
    it('exclui um usuário sem empréstimos', async () => {
      const usuario = criarUsuarioFake()
      usuarios.usuarios.push(usuario)

      const excluir = new ExcluirUsuario(usuarios)
      await excluir.executar(usuario.id)

      expect(await usuarios.buscarPorId(usuario.id)).toBeNull()
    })

    it('recusa excluir usuário com empréstimos registrados', async () => {
      const usuario = criarUsuarioFake()
      usuarios.usuarios.push(usuario)
      usuarios.emprestimosRegistrados = 1

      const excluir = new ExcluirUsuario(usuarios)

      await expect(excluir.executar(usuario.id)).rejects.toMatchObject({
        codigo: 'USUARIO_COM_EMPRESTIMOS',
        statusCode: 409,
      })
      expect(await usuarios.buscarPorId(usuario.id)).not.toBeNull()
    })
  })
})
