import { z } from 'zod'

/**
 * Schemas de entrada da API (validação com Zod).
 *
 * Validar na borda é uma decisão de arquitetura: o domínio pode confiar que
 * os dados chegaram no formato certo. Nenhum caso de uso precisa checar
 * "isso é string?", "esse e-mail é válido?".
 *
 * `.strict()` recusa campos desconhecidos. Isso evita que um erro de digitação
 * do cliente (ex.: "email" em vez de "e-mail") passe silenciosamente.
 */

export const esquemaNovoLivro = z
  .object({
    titulo: z.string().trim().min(1, 'titulo é obrigatório').max(200),
    autor: z.string().trim().min(1, 'autor é obrigatório').max(200),
    isbn: z.string().trim().min(10, 'isbn deve ter ao menos 10 caracteres').max(20),
    // z.coerce aceita 3 e "3", o que é amigável para quem testa com curl.
    exemplaresTotal: z.coerce.number().int().min(1).max(10_000),
  })
  .strict()

export const esquemaNovoUsuario = z
  .object({
    nome: z.string().trim().min(1, 'nome é obrigatório').max(200),
    email: z.string().trim().email('email inválido').max(200),
  })
  .strict()

export const esquemaNovoEmprestimo = z
  .object({
    livroId: z.string().uuid('livroId deve ser um UUID'),
    usuarioId: z.string().uuid('usuarioId deve ser um UUID'),
  })
  .strict()

export const esquemaParametroId = z.object({
  id: z.string().uuid('id deve ser um UUID'),
})

export type DadosNovoLivroHttp = z.infer<typeof esquemaNovoLivro>
export type DadosNovoUsuarioHttp = z.infer<typeof esquemaNovoUsuario>
export type DadosNovoEmprestimoHttp = z.infer<typeof esquemaNovoEmprestimo>
