// Seed OPCIONAL de volume, usado para o experimento de desempenho.
//
//   npm run db:seed:volume
//
// Cria livros, usuários e empréstimos em massa para que o EXPLAIN ANALYZE
// mostre a diferença de um índice. Não é necessário para a demo funcional.
//
// Cuidado: rode apenas no banco local. Este script APAGA empréstimos antes de
// gerar os dados novos.

import 'dotenv/config'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const QUANTIDADE_DE_LIVROS = 500
const QUANTIDADE_DE_USUARIOS = 1_000
const QUANTIDADE_DE_EMPRESTIMOS = 20_000

async function main(): Promise<void> {
  console.log('Limpando empréstimos existentes...')
  await prisma.emprestimo.deleteMany()

  console.log('Criando livros...')
  const livros = await Promise.all(
    Array.from({ length: QUANTIDADE_DE_LIVROS }, (_, indice) =>
      prisma.livro.upsert({
        where: { isbn: `volume-${indice}` },
        update: {},
        create: {
          titulo: `Livro de volume ${indice}`,
          autor: `Autor ${indice % 50}`,
          isbn: `volume-${indice}`,
          exemplaresTotal: 50,
        },
      }),
    ),
  )

  console.log('Criando usuários...')
  const usuarios = await Promise.all(
    Array.from({ length: QUANTIDADE_DE_USUARIOS }, (_, indice) =>
      prisma.usuario.upsert({
        where: { email: `volume-${indice}@exemplo.com` },
        update: {},
        create: {
          nome: `Usuário volume ${indice}`,
          email: `volume-${indice}@exemplo.com`,
        },
      }),
    ),
  )

  console.log('Criando empréstimos...')
  const agora = Date.now()
  const EM_LOTES = 1_000

  for (let inicio = 0; inicio < QUANTIDADE_DE_EMPRESTIMOS; inicio += EM_LOTES) {
    const lote = Array.from({ length: EM_LOTES }, (_, posicao) => {
      const indice = inicio + posicao
      const diasAtras = indice % 60
      const dataEmprestimo = new Date(agora - diasAtras * 24 * 60 * 60 * 1000)

      return {
        livroId: livros[indice % livros.length]!.id,
        usuarioId: usuarios[indice % usuarios.length]!.id,
        status: 'ATIVO' as const,
        dataEmprestimo,
        dataPrevista: new Date(dataEmprestimo.getTime() + 14 * 24 * 60 * 60 * 1000),
      }
    })

    await prisma.emprestimo.createMany({ data: lote })
    console.log(`  ${inicio + lote.length}/${QUANTIDADE_DE_EMPRESTIMOS}`)
  }

  console.log('Volume pronto.')
}

main()
  .catch((erro) => {
    console.error(erro)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
