-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "status_emprestimo" AS ENUM ('ATIVO', 'DEVOLVIDO');

-- CreateTable
CREATE TABLE "livros" (
    "id" UUID NOT NULL,
    "titulo" TEXT NOT NULL,
    "autor" TEXT NOT NULL,
    "isbn" TEXT NOT NULL,
    "exemplares_total" INTEGER NOT NULL,
    "criado_em" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "livros_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "usuarios" (
    "id" UUID NOT NULL,
    "nome" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "criado_em" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "usuarios_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "emprestimos" (
    "id" UUID NOT NULL,
    "livro_id" UUID NOT NULL,
    "usuario_id" UUID NOT NULL,
    "status" "status_emprestimo" NOT NULL DEFAULT 'ATIVO',
    "data_emprestimo" TIMESTAMP(3) NOT NULL,
    "data_prevista" TIMESTAMP(3) NOT NULL,
    "data_devolucao" TIMESTAMP(3),

    CONSTRAINT "emprestimos_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "livros_isbn_key" ON "livros"("isbn");

-- CreateIndex
CREATE UNIQUE INDEX "usuarios_email_key" ON "usuarios"("email");

-- CreateIndex
CREATE INDEX "emprestimos_livro_id_status_idx" ON "emprestimos"("livro_id", "status");

-- CreateIndex
CREATE INDEX "emprestimos_usuario_id_status_idx" ON "emprestimos"("usuario_id", "status");

-- CreateIndex
CREATE INDEX "emprestimos_status_data_prevista_idx" ON "emprestimos"("status", "data_prevista");

-- AddForeignKey
ALTER TABLE "emprestimos" ADD CONSTRAINT "emprestimos_livro_id_fkey" FOREIGN KEY ("livro_id") REFERENCES "livros"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "emprestimos" ADD CONSTRAINT "emprestimos_usuario_id_fkey" FOREIGN KEY ("usuario_id") REFERENCES "usuarios"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
