import type { Emprestimo } from '../domain/entidades'
import type {
  LivroRepositorio,
  UsuarioRepositorio,
  EmprestimoRepositorio,
} from '../domain/repositorios'
import { erros } from '../domain/erros'
import type { Relogio } from '../domain/relogio'
import { relogioDoSistema } from '../domain/relogio'
import {
  calcularDataPrevista,
  LIMITE_PADRAO_DE_EMPRESTIMOS,
  PRAZO_PADRAO_EM_DIAS,
  validarEmprestimo,
} from '../domain/regras'

export interface EntradaEmprestarLivro {
  livroId: string
  usuarioId: string
}

/**
 * Caso de uso: emprestar um livro.
 *
 * Um caso de uso é a "receita" de uma operação: orquestra repositórios,
 * aplica as regras do domínio e devolve o resultado. Ele não sabe nada de
 * HTTP (status code, JSON) nem de SQL. Essa separação é o S do SOLID
 * (Single Responsibility) na prática.
 */
export class EmprestarLivro {
  constructor(
    private readonly livros: LivroRepositorio,
    private readonly usuarios: UsuarioRepositorio,
    private readonly emprestimos: EmprestimoRepositorio,
    // Dependências com valor padrão: em produção usa o relógio do sistema e
    // as regras padrão; em teste injetamos valores controlados.
    private readonly relogio: Relogio = relogioDoSistema,
    private readonly prazoEmDias: number = PRAZO_PADRAO_EM_DIAS,
    private readonly limiteDeEmprestimos: number = LIMITE_PADRAO_DE_EMPRESTIMOS,
  ) {}

  async executar({ livroId, usuarioId }: EntradaEmprestarLivro): Promise<Emprestimo> {
    // 1) Verificações de existência -> erro 404 com mensagem clara.
    const livro = await this.livros.buscarPorId(livroId)
    if (!livro) throw erros.livroNaoEncontrado()

    const usuario = await this.usuarios.buscarPorId(usuarioId)
    if (!usuario) throw erros.usuarioNaoEncontrado()

    // 2) Calculamos as datas a partir do MESMO instante para não haver
    //    diferença de milissegundos entre empréstimo e vencimento.
    const agora = this.relogio.agora()
    const dataPrevista = calcularDataPrevista(agora, this.prazoEmDias)

    // 3) O repositório abre transação, bloqueia o livro e só grava depois de
    //    chamar `validarEmprestimo` com o estado real do banco.
    return this.emprestimos.criarComBloqueio(
      { livroId, usuarioId, dataEmprestimo: agora, dataPrevista },
      (estado) => validarEmprestimo(estado, this.limiteDeEmprestimos),
    )
  }
}
