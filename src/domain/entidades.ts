/**
 * Entidades do domínio.
 *
 * São tipos "puros": não sabem que existe Prisma, Fastify ou PostgreSQL.
 * Isso é o que permite testar as regras de negócio sem subir banco nenhum.
 * Os nomes batem com as colunas mapeadas no schema.prisma para não precisar
 * de conversão entre camadas.
 */

/** Um empréstimo só pode estar em um destes dois estados. */
export type StatusEmprestimo = 'ATIVO' | 'DEVOLVIDO'

export interface Livro {
  id: string
  titulo: string
  autor: string
  isbn: string
  /** Quantos exemplares físicos a biblioteca possui. */
  exemplaresTotal: number
  criadoEm: Date
}

export interface Usuario {
  id: string
  nome: string
  email: string
  criadoEm: Date
}

export interface Emprestimo {
  id: string
  livroId: string
  usuarioId: string
  status: StatusEmprestimo
  dataEmprestimo: Date
  /** Data limite para devolver (sempre à meia-noite UTC). */
  dataPrevista: Date
  /** null enquanto o livro não foi devolvido. */
  dataDevolucao: Date | null
}

/**
 * Empréstimo com os dados do livro e do usuário já incluídos.
 * Usado na listagem de atrasados, que precisa mostrar "quem" e "qual livro".
 */
export interface EmprestimoDetalhado extends Emprestimo {
  livro: Pick<Livro, 'id' | 'titulo' | 'autor'>
  usuario: Pick<Usuario, 'id' | 'nome' | 'email'>
}

/**
 * Livro + números calculados na hora da consulta.
 * "exemplaresDisponiveis" NÃO é uma coluna do banco: é sempre recalculado
 * para não ficar desatualizado (ver ADR 0001).
 */
export interface LivroComDisponibilidade extends Livro {
  emprestimosAtivos: number
  exemplaresDisponiveis: number
}
