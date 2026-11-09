// Seed = dados iniciais para demonstrar a API sem digitar 300 curls.
//
// Rodar com:
//   npm run db:seed
//
// É idempotente: usa upsert pelo isbn/email, então pode rodar várias vezes.

import 'dotenv/config'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main(): Promise<void> {
  const livros = [
    {
      titulo: 'Clean Code',
      autor: 'Robert C. Martin',
      isbn: '9780132350884',
      exemplaresTotal: 3,
    },
    {
      titulo: 'Refactoring',
      autor: 'Martin Fowler',
      isbn: '9780201485677',
      exemplaresTotal: 2,
    },
    {
      titulo: 'Domain-Driven Design',
      autor: 'Eric Evans',
      isbn: '9780321125217',
      exemplaresTotal: 1,
    },
    {
      titulo: 'Implementing Domain-Driven Design',
      autor: 'Vaughn Vernon',
      isbn: '9780321834577',
      exemplaresTotal: 2,
    },
    {
      titulo: 'The Pragmatic Programmer',
      autor: 'Andrew Hunt e David Thomas',
      isbn: '9780201616224',
      exemplaresTotal: 2,
    },
    {
      titulo: 'Design Patterns',
      autor: 'Erich Gamma, Richard Helm, Ralph Johnson e John Vlissides',
      isbn: '9780201633610',
      exemplaresTotal: 1,
    },
    {
      titulo: 'Working Effectively with Legacy Code',
      autor: 'Michael Feathers',
      isbn: '9780131177055',
      exemplaresTotal: 2,
    },
    {
      titulo: 'Test-Driven Development',
      autor: 'Kent Beck',
      isbn: '9780321146533',
      exemplaresTotal: 2,
    },
    {
      titulo: 'Continuous Delivery',
      autor: 'Jez Humble e David Farley',
      isbn: '9780321601919',
      exemplaresTotal: 1,
    },
    {
      titulo: 'Accelerate',
      autor: 'Nicole Forsgren, Jez Humble e Gene Kim',
      isbn: '9781942788331',
      exemplaresTotal: 2,
    },
  ]

  const usuarios = [
    { nome: 'Ana Souza', email: 'ana@exemplo.com' },
    { nome: 'Bruno Lima', email: 'bruno@exemplo.com' },
    { nome: 'Carla Dias', email: 'carla@exemplo.com' },
    { nome: 'Diego Alves', email: 'diego@exemplo.com' },
    { nome: 'Elisa Martins', email: 'elisa@exemplo.com' },
  ]

  for (const livro of livros) {
    await prisma.livro.upsert({
      where: { isbn: livro.isbn },
      update: livro,
      create: livro,
    })
  }

  for (const usuario of usuarios) {
    await prisma.usuario.upsert({
      where: { email: usuario.email },
      update: usuario,
      create: usuario,
    })
  }

  console.log(`${livros.length} livros e ${usuarios.length} usuários prontos.`)
}

main()
  .catch((erro) => {
    console.error(erro)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
