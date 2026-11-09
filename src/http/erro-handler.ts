import { Prisma } from '@prisma/client'
import type { FastifyError, FastifyInstance } from 'fastify'
import { ErroDeDominio, erros } from '../domain/erros'

/**
 * Tratamento central de erros.
 *
 * Ter UM lugar que decide o formato da resposta de erro é o que mantém a API
 * previsível. Toda rota pode simplesmente `throw` — quem responde é daqui.
 *
 * Formato único:
 *   { "erro": { "codigo": "...", "mensagem": "...", "detalhes": ... } }
 */
export function registrarTratamentoDeErros(app: FastifyInstance): void {
  app.setErrorHandler((erro: FastifyError, requisicao, resposta) => {
    // 1) Erros de negócio: já vêm com status e código prontos.
    if (erro instanceof ErroDeDominio) {
      return resposta.status(erro.statusCode).send({
        erro: {
          codigo: erro.codigo,
          mensagem: erro.message,
          ...(erro.detalhes === undefined ? {} : { detalhes: erro.detalhes }),
        },
      })
    }

    // 2) Violação de campo único (isbn ou email repetido). O Prisma devolve
    //    P2002 e nós traduzimos para o vocabulário da API.
    if (erro instanceof Prisma.PrismaClientKnownRequestError && erro.code === 'P2002') {
      const alvo = erro.meta?.target
      const campo = Array.isArray(alvo) ? alvo.join(', ') : String(alvo ?? 'campo único')
      const conflito = erros.valorJaCadastrado(campo)

      return resposta.status(conflito.statusCode).send({
        erro: { codigo: conflito.codigo, mensagem: conflito.message },
      })
    }

    // 3) JSON malformado enviado pelo cliente.
    if (erro.statusCode === 400) {
      return resposta.status(400).send({
        erro: { codigo: 'REQUISICAO_INVALIDA', mensagem: erro.message },
      })
    }

    // 4) Qualquer coisa inesperada: loga com stack trace e NÃO expõe detalhe
    //    interno para o cliente (segurança).
    requisicao.log.error({ err: erro }, 'erro_nao_tratado')

    return resposta.status(500).send({
      erro: {
        codigo: 'ERRO_INTERNO',
        mensagem: 'Erro interno inesperado. Tente novamente mais tarde.',
      },
    })
  })

  // Rota inexistente também segue o formato padrão.
  app.setNotFoundHandler((requisicao, resposta) => {
    return resposta.status(404).send({
      erro: {
        codigo: 'ROTA_NAO_ENCONTRADA',
        mensagem: `A rota ${requisicao.method} ${requisicao.url} não existe.`,
      },
    })
  })
}
