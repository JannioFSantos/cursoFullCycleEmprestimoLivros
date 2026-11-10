import { randomUUID } from 'node:crypto'
import type {
  Emprestimo,
  EmprestimoDetalhado,
  Livro,
  LivroComDisponibilidade,
  Usuario,
} from '../../src/domain/entidades'
import type {
  DadosNovoLivro,
  DadosNovoEmprestimo,
  DadosNovoUsuario,
  EmprestimoRepositorio,
  LivroRepositorio,
  UsuarioRepositorio,
} from '../../src/domain/repositorios'
import type { EstadoParaEmprestar, EstadoParaAtualizarLivro } from '../../src/domain/regras'
import {
  calcularDisponiveis,
  decidirModoDeExclusao,
  inicioDoDia,
} from '../../src/domain/regras'
import { erros } from '../../src/domain/erros'

/**
 * Dublês (fakes) dos repositórios para os testes unitários.
 *
 * Eles imitam o comportamento do Prisma em memória. O objetivo não é testar o
 * banco (isso é papel do teste de integração), e sim testar o caso de uso e
 * as regras de negócio em milissegundos.
 */

export function criarLivroFake(
  dados: Partial<Livro> & Pick<Livro, 'exemplaresTotal'>,
): Livro {
  return {
    id: randomUUID(),
    titulo: 'Livro de teste',
    autor: 'Autor de teste',
    isbn: `isbn-${randomUUID()}`,
    criadoEm: new Date(),
    excluidoEm: null,
    ...dados,
  }
}

export function criarUsuarioFake(dados: Partial<Usuario> = {}): Usuario {
  return {
    id: randomUUID(),
    nome: 'Usuário de teste',
    email: `${randomUUID()}@exemplo.com`,
    criadoEm: new Date(),
    excluidoEm: null,
    ...dados,
  }
}

export class LivroRepositorioFake implements LivroRepositorio {
  readonly livros: Livro[] = []

  /** Números usados pelos testes de edição/exclusão. */
  emprestimosAtivos = 0
  emprestimosRegistrados = 0

  async criar(dados: DadosNovoLivro): Promise<Livro> {
    const livro: Livro = {
      id: randomUUID(),
      criadoEm: new Date(),
      excluidoEm: null,
      ...dados,
    }
    this.livros.push(livro)
    return livro
  }

  async buscarPorId(id: string): Promise<Livro | null> {
    return (
      this.livros.find((livro) => livro.id === id && livro.excluidoEm === null) ??
      null
    )
  }

  async listarComDisponibilidade(): Promise<LivroComDisponibilidade[]> {
    return this.livros
      .filter((livro) => livro.excluidoEm === null)
      .map((livro) => ({
        ...livro,
        emprestimosAtivos: 0,
        exemplaresDisponiveis: calcularDisponiveis(livro.exemplaresTotal, 0),
      }))
  }

  async atualizarComBloqueio(
    id: string,
    dados: DadosNovoLivro,
    validar: (estado: EstadoParaAtualizarLivro) => void,
  ): Promise<Livro> {
    const livro = await this.buscarPorId(id)
    if (!livro) throw erros.livroNaoEncontrado()

    validar({
      exemplaresTotal: dados.exemplaresTotal,
      emprestimosAtivos: this.emprestimosAtivos,
    })

    Object.assign(livro, dados)
    return livro
  }

  async excluir(id: string, quando: Date): Promise<void> {
    const indice = this.livros.findIndex(
      (livro) => livro.id === id && livro.excluidoEm === null,
    )
    if (indice < 0) throw erros.livroNaoEncontrado()

    // Mesma decisão do domínio usada pela implementação Prisma.
    if (decidirModoDeExclusao(this.emprestimosRegistrados) === 'APAGAR') {
      this.livros.splice(indice, 1)
      return
    }

    this.livros[indice].excluidoEm = quando
  }
}

export class UsuarioRepositorioFake implements UsuarioRepositorio {
  readonly usuarios: Usuario[] = []

  /** Quantidade usada pelo teste de exclusão de usuário. */
  emprestimosRegistrados = 0

  async criar(dados: DadosNovoUsuario): Promise<Usuario> {
    const usuario: Usuario = {
      id: randomUUID(),
      criadoEm: new Date(),
      excluidoEm: null,
      ...dados,
    }
    this.usuarios.push(usuario)
    return usuario
  }

  async buscarPorId(id: string): Promise<Usuario | null> {
    return (
      this.usuarios.find(
        (usuario) => usuario.id === id && usuario.excluidoEm === null,
      ) ?? null
    )
  }

  async listar(): Promise<Usuario[]> {
    return this.usuarios
      .filter((usuario) => usuario.excluidoEm === null)
      .sort((a, b) => a.nome.localeCompare(b.nome))
  }

  async atualizar(id: string, dados: DadosNovoUsuario): Promise<Usuario> {
    const usuario = await this.buscarPorId(id)
    if (!usuario) throw erros.usuarioNaoEncontrado()

    Object.assign(usuario, dados)
    return usuario
  }

  async excluir(id: string, quando: Date): Promise<void> {
    const indice = this.usuarios.findIndex(
      (usuario) => usuario.id === id && usuario.excluidoEm === null,
    )
    if (indice < 0) throw erros.usuarioNaoEncontrado()

    if (decidirModoDeExclusao(this.emprestimosRegistrados) === 'APAGAR') {
      this.usuarios.splice(indice, 1)
      return
    }

    this.usuarios[indice].excluidoEm = quando
  }
}

export class EmprestimoRepositorioFake implements EmprestimoRepositorio {
  readonly emprestimos: Emprestimo[] = []

  constructor(
    private readonly livros: LivroRepositorioFake,
    private readonly usuarios: UsuarioRepositorioFake,
  ) {}

  async criarComBloqueio(
    dados: DadosNovoEmprestimo,
    validar: (estado: EstadoParaEmprestar) => void,
  ): Promise<Emprestimo> {
    const livro = await this.livros.buscarPorId(dados.livroId)
    if (!livro) throw erros.livroNaoEncontrado()

    const usuario = await this.usuarios.buscarPorId(dados.usuarioId)
    if (!usuario) throw erros.usuarioNaoEncontrado()

    const ativosDoLivro = this.emprestimos.filter(
      (emprestimo) =>
        emprestimo.livroId === dados.livroId && emprestimo.status === 'ATIVO',
    ).length

    const ativosDoUsuario = this.emprestimos.filter(
      (emprestimo) =>
        emprestimo.usuarioId === dados.usuarioId && emprestimo.status === 'ATIVO',
    ).length

    const hoje = inicioDoDia(dados.dataEmprestimo)
    const temAtraso = this.emprestimos.some(
      (emprestimo) =>
        emprestimo.usuarioId === dados.usuarioId &&
        emprestimo.status === 'ATIVO' &&
        inicioDoDia(emprestimo.dataPrevista) < hoje,
    )

    // Mesma função pura usada em produção.
    validar({
      exemplaresTotal: livro.exemplaresTotal,
      emprestimosAtivosDoLivro: ativosDoLivro,
      emprestimosAtivosDoUsuario: ativosDoUsuario,
      usuarioTemAtraso: temAtraso,
    })

    const emprestimo: Emprestimo = {
      id: randomUUID(),
      livroId: dados.livroId,
      usuarioId: dados.usuarioId,
      status: 'ATIVO',
      dataEmprestimo: dados.dataEmprestimo,
      dataPrevista: dados.dataPrevista,
      dataDevolucao: null,
    }

    this.emprestimos.push(emprestimo)
    return emprestimo
  }

  async buscarPorId(id: string): Promise<Emprestimo | null> {
    return this.emprestimos.find((emprestimo) => emprestimo.id === id) ?? null
  }

  async registrarDevolucao(id: string, dataDevolucao: Date): Promise<Emprestimo> {
    const emprestimo = await this.buscarPorId(id)
    if (!emprestimo) throw erros.emprestimoNaoEncontrado()

    emprestimo.status = 'DEVOLVIDO'
    emprestimo.dataDevolucao = dataDevolucao
    return emprestimo
  }

  async listarAtrasados(hoje: Date): Promise<EmprestimoDetalhado[]> {
    const detalhados: EmprestimoDetalhado[] = []

    for (const emprestimo of this.emprestimos) {
      if (emprestimo.status !== 'ATIVO') continue
      if (inicioDoDia(emprestimo.dataPrevista) >= inicioDoDia(hoje)) continue

      // Aqui a busca é direto na lista, sem filtrar `excluidoEm`: o histórico
      // precisa continuar aparecendo mesmo para livro/usuário excluídos.
      const livro = this.livros.livros.find(
        (item) => item.id === emprestimo.livroId,
      )
      const usuario = this.usuarios.usuarios.find(
        (item) => item.id === emprestimo.usuarioId,
      )
      if (!livro || !usuario) continue

      detalhados.push({
        ...emprestimo,
        livro: {
          id: livro.id,
          titulo: livro.titulo,
          autor: livro.autor,
          excluidoEm: livro.excluidoEm,
        },
        usuario: {
          id: usuario.id,
          nome: usuario.nome,
          email: usuario.email,
          excluidoEm: usuario.excluidoEm,
        },
      })
    }

    return detalhados
  }

  async listarDetalhados(): Promise<EmprestimoDetalhado[]> {
    const detalhados: EmprestimoDetalhado[] = []

    for (const emprestimo of this.emprestimos) {
      const livro = this.livros.livros.find(
        (item) => item.id === emprestimo.livroId,
      )
      const usuario = this.usuarios.usuarios.find(
        (item) => item.id === emprestimo.usuarioId,
      )
      if (!livro || !usuario) continue

      detalhados.push({
        ...emprestimo,
        livro: {
          id: livro.id,
          titulo: livro.titulo,
          autor: livro.autor,
          excluidoEm: livro.excluidoEm,
        },
        usuario: {
          id: usuario.id,
          nome: usuario.nome,
          email: usuario.email,
          excluidoEm: usuario.excluidoEm,
        },
      })
    }

    return detalhados.sort(
      (a, b) => b.dataEmprestimo.getTime() - a.dataEmprestimo.getTime(),
    )
  }
}
