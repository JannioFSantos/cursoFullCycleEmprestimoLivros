/**
 * ErroDeDominio = uma regra de negócio foi violada.
 *
 * A grande vantagem de ter um erro próprio é que a camada HTTP não precisa
 * "adivinhar" o status: cada erro já carrega o código HTTP correto e um código
 * de erro estável (LIVRO_INDISPONIVEL, USUARIO_COM_ATRASO, ...) que o cliente
 * da API pode usar para tratar o caso.
 *
 * Regra prática deste projeto:
 *   404 -> o recurso não existe
 *   409 -> o recurso existe, mas a operação conflita com uma regra
 *   400 -> os dados enviados estão inválidos
 */
export class ErroDeDominio extends Error {
  readonly codigo: string
  readonly statusCode: number
  readonly detalhes?: unknown

  constructor(codigo: string, mensagem: string, statusCode = 409, detalhes?: unknown) {
    super(mensagem)
    this.name = 'ErroDeDominio'
    this.codigo = codigo
    this.statusCode = statusCode
    this.detalhes = detalhes
  }
}

/**
 * Fábrica de erros: centraliza as mensagens e evita espalhar strings soltas
 * pelo código. Se amanhã a mensagem mudar, muda só aqui.
 */
export const erros = {
  livroNaoEncontrado: () =>
    new ErroDeDominio('LIVRO_NAO_ENCONTRADO', 'Livro não encontrado.', 404),

  usuarioNaoEncontrado: () =>
    new ErroDeDominio('USUARIO_NAO_ENCONTRADO', 'Usuário não encontrado.', 404),

  emprestimoNaoEncontrado: () =>
    new ErroDeDominio('EMPRESTIMO_NAO_ENCONTRADO', 'Empréstimo não encontrado.', 404),

  livroIndisponivel: () =>
    new ErroDeDominio(
      'LIVRO_INDISPONIVEL',
      'Não há exemplar disponível para este livro.',
      409,
    ),

  usuarioComAtraso: () =>
    new ErroDeDominio(
      'USUARIO_COM_ATRASO',
      'O usuário possui empréstimo em atraso e não pode pegar outro livro.',
      409,
    ),

  limiteAtingido: (limite: number) =>
    new ErroDeDominio(
      'LIMITE_ATINGIDO',
      `O usuário já possui ${limite} empréstimos ativos.`,
      409,
    ),

  emprestimoJaDevolvido: () =>
    new ErroDeDominio('EMPRESTIMO_JA_DEVOLVIDO', 'Este empréstimo já foi devolvido.', 409),

  dadosInvalidos: (detalhes: unknown) =>
    new ErroDeDominio('DADOS_INVALIDOS', 'Dados da requisição inválidos.', 400, detalhes),

  valorJaCadastrado: (campo: string) =>
    new ErroDeDominio(
      'VALOR_JA_CADASTRADO',
      `Já existe um registro com este ${campo}.`,
      409,
    ),
}
