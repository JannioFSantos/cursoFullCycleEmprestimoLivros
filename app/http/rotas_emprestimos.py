"""Rotas de empréstimo — o fluxo principal do projeto.

POST   /emprestimos               -> cria (201) ou recusa com regra (409)
PATCH  /emprestimos/:id/devolucao -> devolve (200)
GET    /emprestimos/atrasados     -> lista quem está devendo (200)
GET    /emprestimos               -> lista completa, com livro e usuário
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.domain.erros import ErroDeDominio
from app.http.dependencias import Dependencias
from app.http.esquemas import EsquemaNovoEmprestimo, EsquemaParametroId
from app.http.requisicao import corpo_json
from app.http.serializacao import (
    serializar_emprestimo,
    serializar_emprestimo_detalhado,
)
from app.http.validacao import validar
from app.use_cases.emprestar_livro import EntradaEmprestarLivro


def registrar_rotas_de_emprestimos(bp: Blueprint, deps: Dependencias) -> None:
    @bp.post("/emprestimos")
    def criar_emprestimo():
        dados = validar(EsquemaNovoEmprestimo, corpo_json())

        try:
            emprestimo = deps.emprestar_livro.executar(
                EntradaEmprestarLivro(
                    livro_id=dados.livro_id,
                    usuario_id=dados.usuario_id,
                )
            )
            deps.metricas.emprestimos.labels(resultado="criado").inc()
            return jsonify(serializar_emprestimo(emprestimo)), 201
        except ErroDeDominio:
            # Recusa de negócio (sem exemplar, atraso, limite) também é um
            # número que interessa: se disparar, algo mudou no comportamento.
            deps.metricas.emprestimos.labels(resultado="recusado").inc()
            # Repassa para o error handler central montar a resposta.
            raise

    @bp.patch("/emprestimos/<string:id>/devolucao")
    def devolver_emprestimo(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        emprestimo = deps.devolver_emprestimo.executar(identificador)
        return jsonify(serializar_emprestimo(emprestimo)), 200

    @bp.get("/emprestimos/atrasados")
    def listar_atrasados():
        # Usa o mesmo relógio injetado: em teste conseguimos "viajar no tempo".
        itens = [
            serializar_emprestimo_detalhado(emprestimo)
            for emprestimo in deps.emprestimos.listar_atrasados(
                deps.relogio.agora()
            )
        ]
        return jsonify({"itens": itens})

    # Lista completa, com livro e usuário, usada pela tela de demonstração.
    @bp.get("/emprestimos")
    def listar_emprestimos():
        itens = [
            serializar_emprestimo_detalhado(emprestimo)
            for emprestimo in deps.emprestimos.listar_detalhados()
        ]
        return jsonify({"itens": itens})
