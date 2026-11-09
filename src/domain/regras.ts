import type { Emprestimo } from './entidades'
import { erros } from './erros'

/**
 * Regras de negócio puras da biblioteca.
 *
 * "Pura" significa: recebe dados, devolve dados (ou lança erro) e não acessa
 * banco, rede, relógio do sistema nem variável global. Isso torna cada regra
 * trivial de testar e de explicar em uma apresentação.
 */

/** Prazo padrão de devolução, em dias. Pode ser sobrescrito por PRAZO_DIAS. */
export const PRAZO_PADRAO_EM_DIAS = 14

/** Quantos empréstimos simultâneos um usuário pode ter. */
export const LIMITE_PADRAO_DE_EMPRESTIMOS = 3

/**
 * Zera horas/minutos/segundos em UTC.
 *
 * Trabalhamos com datas "de calendário": um livro que vence hoje ainda NÃO
 * está atrasado, independentemente do horário em que foi emprestado. Fazer
 * essa conta em UTC evita bug de fuso horário no servidor.
 */
export function inicioDoDia(data: Date): Date {
  return new Date(
    Date.UTC(data.getUTCFullYear(), data.getUTCMonth(), data.getUTCDate()),
  )
}

/**
 * Calcula a data de devolução: dia do empréstimo + prazo, à meia-noite UTC.
 * Ex.: emprestado em 05/01 com prazo de 14 dias -> previsto para 19/01 00:00.
 */
export function calcularDataPrevista(dataEmprestimo: Date, prazoEmDias: number): Date {
  const prevista = inicioDoDia(dataEmprestimo)
  prevista.setUTCDate(prevista.getUTCDate() + prazoEmDias)
  return prevista
}

/**
 * Disponibilidade = total de exemplares - empréstimos ativos.
 * Pode ser negativa? Não deveria, mas nunca deixamos o número passar de total.
 */
export function calcularDisponiveis(
  exemplaresTotal: number,
  emprestimosAtivos: number,
): number {
  return Math.max(0, exemplaresTotal - emprestimosAtivos)
}

/**
 * Um empréstimo está atrasado quando ainda está ATIVO e a data prevista é
 * anterior ao dia de hoje. "Vence hoje" não conta como atraso.
 */
export function estaAtrasado(
  emprestimo: Pick<Emprestimo, 'status' | 'dataPrevista'>,
  hoje: Date,
): boolean {
  if (emprestimo.status !== 'ATIVO') return false
  return inicioDoDia(emprestimo.dataPrevista) < inicioDoDia(hoje)
}

/** Estado atual do livro + usuário, coletado antes de decidir o empréstimo. */
export interface EstadoParaEmprestar {
  exemplaresTotal: number
  emprestimosAtivosDoLivro: number
  emprestimosAtivosDoUsuario: number
  usuarioTemAtraso: boolean
}

/** Estado do livro no momento de editar a quantidade de exemplares. */
export interface EstadoParaAtualizarLivro {
  exemplaresTotal: number
  emprestimosAtivos: number
}

/**
 * Não deixa reduzir os exemplares abaixo do que já está emprestado.
 * Ex.: o livro tem 3 exemplares e 2 ativos; o mínimo agora é 2.
 */
export function validarAtualizacaoDeLivro(estado: EstadoParaAtualizarLivro): void {
  if (estado.exemplaresTotal < estado.emprestimosAtivos) {
    throw erros.exemplaresAbaixoDosEmprestimos(
      estado.exemplaresTotal,
      estado.emprestimosAtivos,
    )
  }
}

/**
 * Livro com qualquer empréstimo (ativo ou devolvido) não pode ser excluído.
 * Escolhi bloquear com histórico também para não apagar o passado: o
 * empréstimo é um registro que a biblioteca precisa guardar.
 */
export function validarExclusaoDeLivro(emprestimosRegistrados: number): void {
  if (emprestimosRegistrados > 0) {
    throw erros.livroComEmprestimos(emprestimosRegistrados)
  }
}

/** Mesma ideia da exclusão de livro: usuário com histórico não é apagado. */
export function validarExclusaoDeUsuario(emprestimosRegistrados: number): void {
  if (emprestimosRegistrados > 0) {
    throw erros.usuarioComEmprestimos(emprestimosRegistrados)
  }
}

/**
 * Valida as três regras de empréstimo na ordem em que fazem sentido para o
 * usuário: primeiro "tem livro?", depois "você está em atraso?", depois
 * "atingiu o limite?".
 *
 * Lançar erro em vez de retornar boolean é proposital: o caso de uso não
 * precisa ficar montando if/else, e a mensagem já sai pronta para a API.
 */
export function validarEmprestimo(
  estado: EstadoParaEmprestar,
  limiteDeEmprestimos: number = LIMITE_PADRAO_DE_EMPRESTIMOS,
): void {
  const disponiveis = calcularDisponiveis(
    estado.exemplaresTotal,
    estado.emprestimosAtivosDoLivro,
  )

  if (disponiveis <= 0) throw erros.livroIndisponivel()
  if (estado.usuarioTemAtraso) throw erros.usuarioComAtraso()
  if (estado.emprestimosAtivosDoUsuario >= limiteDeEmprestimos) {
    throw erros.limiteAtingido(limiteDeEmprestimos)
  }
}
