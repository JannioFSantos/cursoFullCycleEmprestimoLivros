import type { z } from 'zod'
import { erros } from '../domain/erros'

/**
 * Valida `dados` contra um schema Zod e devolve o valor tipado.
 *
 * Se falhar, lança DADOS_INVALIDOS (400) já com o detalhe por campo. Assim o
 * cliente recebe algo como:
 *
 *   { "erro": { "codigo": "DADOS_INVALIDOS", "detalhes": { "email": ["email inválido"] } } }
 */
export function validar<T>(esquema: z.ZodType<T>, dados: unknown): T {
  const resultado = esquema.safeParse(dados)

  if (!resultado.success) {
    throw erros.dadosInvalidos(resultado.error.flatten().fieldErrors)
  }

  return resultado.data
}
