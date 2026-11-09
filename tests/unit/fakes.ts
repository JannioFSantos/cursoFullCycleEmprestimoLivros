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
import type { EstadoParaEmprestar } from '../../src/domain/regras'
import { calcularDisponiveis, inicioDoDia } from '../../src/domain/regras'
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
    ...dados,
  }
}

export function criarUsuarioFake(dados: Partial<Usuario> = {}): Usuario {
  return {
    id: randomUUID(),
    nome: 'Usuário de teste',
    email: `${randomUUID()}@exemplo.com`,
    criadoEm: new Date(),
    ...dados,
  }
}

export class LivroRepositorioFake implements LivroRepositorio {
  readonly livros: Livro[] = []

  async criar(dados: DadosNovoLivro): Promise<Livro> {
    const livro: Livro = { id: randomUUID(), criadoEm: new Date(), ...dados }
    this.livros.push(livro)
    return livro
  }

  async buscarPorId(id: string): Promise<Livro | null> {
    return this.livros.find((livro) => livro.id === id) ?? null
  }

  async listarComDisponibilidade(): Promise<LivroComDisponibilidade[]> {
    return this.livros.map((livro) => ({
      ...livro,
      emprestimosAtivos: 0,
      exemplaresDisponiveis: calcularDisponiveis(livro.exemplaresTotal, 0),
    }))
  }
}

export class UsuarioRepositorioFake implements UsuarioRepositorio {
  readonly usuarios: Usuario[] = []

  async criar(dados: DadosNovoUsuario): Promise<Usuario> {
    const usuario: Usuario = { id: randomUUID(), criadoEm: new Date(), ...dados }
    this.usuarios.push(usuario)
    return usuario
  }

  async buscarPorId(id: string): Promise<Usuario | null> {
    return this.usuarios.find((usuario) => usuario.id === id) ?? null
  }

  async listar(): Promise<Usuario[]> {
    return [...this.usuarios].sort((a, b) => a.nome.localeCompare(b.nome))
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

      const livro = await this.livros.buscarPorId(emprestimo.livroId)
      const usuario = await this.usuarios.buscarPorId(emprestimo.usuarioId)
      if (!livro || !usuario) continue

      detalhados.push({
        ...emprestimo,
        livro: { id: livro.id, titulo: livro.titulo, autor: livro.autor },
        usuario: { id: usuario.id, nome: usuario.nome, email: usuario.email },
      })
    }

    return detalhados
  }

  async listarDetalhados(): Promise<EmprestimoDetalhado[]> {
    const detalhados: EmprestimoDetalhado[] = []

    for (const emprestimo of this.emprestimos) {
      const livro = await this.livros.buscarPorId(emprestimo.livroId)
      const usuario = await this.usuarios.buscarPorId(emprestimo.usuarioId)
      if (!livro || !usuario) continue

      detalhados.push({
        ...emprestimo,
        livro: { id: livro.id, titulo: livro.titulo, autor: livro.autor },
        usuario: { id: usuario.id, nome: usuario.nome, email: usuario.email },
      })
    }

    return detalhados.sort(
      (a, b) => b.dataEmprestimo.getTime() - a.dataEmprestimo.getTime(),
    )
  }
}
