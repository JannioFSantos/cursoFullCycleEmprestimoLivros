import type {
  Emprestimo,
  EmprestimoDetalhado,
  Livro,
  LivroComDisponibilidade,
  Usuario,
} from './entidades'
import type { EstadoParaEmprestar } from './regras'

/**
 * Portas (interfaces) de acesso a dados.
 *
 * O domínio e os casos de uso dependem SÓ destas interfaces. Quem implementa
 * é a pasta src/infra, com Prisma. Isso é o padrão Repository e é o que
 * permite trocar o banco (ou usar um fake nos testes) sem tocar nas regras.
 *
 * Em outras palavras: o "contrato" mora aqui, a "implementação" mora em infra.
 */

export interface DadosNovoLivro {
  titulo: string
  autor: string
  isbn: string
  exemplaresTotal: number
}

export interface DadosNovoUsuario {
  nome: string
  email: string
}

export interface DadosNovoEmprestimo {
  livroId: string
  usuarioId: string
  dataEmprestimo: Date
  dataPrevista: Date
}

export interface LivroRepositorio {
  criar(dados: DadosNovoLivro): Promise<Livro>
  buscarPorId(id: string): Promise<Livro | null>
  listarComDisponibilidade(): Promise<LivroComDisponibilidade[]>
}

export interface UsuarioRepositorio {
  criar(dados: DadosNovoUsuario): Promise<Usuario>
  buscarPorId(id: string): Promise<Usuario | null>
}

export interface EmprestimoRepositorio {
  /**
   * Cria o empréstimo de forma atômica: bloqueia o livro, conta os ativos e
   * chama `validar` ANTES de gravar. Se `validar` lançar erro, nada é gravado.
   *
   * Receber a função de validação aqui é o que mantém a regra no domínio
   * (função pura) e a atomicidade no banco (transação). Detalhe em
   * docs/adr/0001-disponibilidade.md.
   */
  criarComBloqueio(
    dados: DadosNovoEmprestimo,
    validar: (estado: EstadoParaEmprestar) => void,
  ): Promise<Emprestimo>

  buscarPorId(id: string): Promise<Emprestimo | null>
  registrarDevolucao(id: string, dataDevolucao: Date): Promise<Emprestimo>
  listarAtrasados(hoje: Date): Promise<EmprestimoDetalhado[]>
}
