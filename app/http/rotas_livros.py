"""Rotas de livros.

POST   /livros       -> cadastra (201)
GET    /livros       -> lista com disponibilidade (200)
PUT    /livros/:id   -> edita todos os campos (200)
DELETE /livros/:id   -> exclui (204)

Repare que a rota é "burra" de propósito: valida a entrada, chama o caso de
uso/repositório e devolve. Regra de negócio fica no domínio/use case.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.http.dependencias import Dependencias
from app.http.esquemas import (
    EsquemaNovoLivro,
    EsquemaParametroId,
    dados_novo_livro,
)
from app.http.requisicao import corpo_json
from app.http.serializacao import (
    serializar_livro,
    serializar_livro_com_disponibilidade,
)
from app.http.validacao import validar


def registrar_rotas_de_livros(bp: Blueprint, deps: Dependencias) -> None:
    @bp.post("/livros")
    def criar_livro():
        dados = validar(EsquemaNovoLivro, corpo_json())
        livro = deps.livros.criar(dados_novo_livro(dados))
        # 201 Created: a convenção para "criei um recurso novo".
        return jsonify(serializar_livro(livro)), 201

    @bp.get("/livros")
    def listar_livros():
        itens = [
            serializar_livro_com_disponibilidade(livro)
            for livro in deps.livros.listar_com_disponibilidade()
        ]
        return jsonify({"itens": itens})

    @bp.put("/livros/<string:id>")
    def atualizar_livro(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        dados = validar(EsquemaNovoLivro, corpo_json())
        livro = deps.atualizar_livro.executar(
            identificador, dados_novo_livro(dados)
        )
        return jsonify(serializar_livro(livro)), 200

    @bp.delete("/livros/<string:id>")
    def excluir_livro(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        deps.excluir_livro.executar(identificador)
        # 204 No Content: deu certo e não há corpo para devolver.
        return "", 204
