"""Rotas de usuários.

POST /usuarios       -> cadastra (201)
GET  /usuarios       -> lista (200)
GET  /usuarios/:id   -> busca por id (200 ou 404)
PUT  /usuarios/:id   -> edita nome e e-mail (200)
DELETE /usuarios/:id -> exclui (204)
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.domain.erros import erros
from app.http.dependencias import Dependencias
from app.http.esquemas import (
    EsquemaNovoUsuario,
    EsquemaParametroId,
    dados_novo_usuario,
)
from app.http.requisicao import corpo_json
from app.http.serializacao import serializar_usuario
from app.http.validacao import validar


def registrar_rotas_de_usuarios(bp: Blueprint, deps: Dependencias) -> None:
    @bp.post("/usuarios")
    def criar_usuario():
        dados = validar(EsquemaNovoUsuario, corpo_json())
        usuario = deps.usuarios.criar(dados_novo_usuario(dados))
        return jsonify(serializar_usuario(usuario)), 201

    # Lista usada pela tela de demonstração (select de usuário e tabela).
    @bp.get("/usuarios")
    def listar_usuarios():
        return jsonify(
            {"itens": [serializar_usuario(u) for u in deps.usuarios.listar()]}
        )

    @bp.get("/usuarios/<string:id>")
    def buscar_usuario(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        usuario = deps.usuarios.buscar_por_id(identificador)

        # Se não existir, o error handler transforma em 404 no formato padrão.
        if usuario is None:
            raise erros.usuario_nao_encontrado()

        return jsonify(serializar_usuario(usuario))

    @bp.put("/usuarios/<string:id>")
    def atualizar_usuario(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        dados = validar(EsquemaNovoUsuario, corpo_json())
        usuario = deps.atualizar_usuario.executar(
            identificador, dados_novo_usuario(dados)
        )
        return jsonify(serializar_usuario(usuario)), 200

    @bp.delete("/usuarios/<string:id>")
    def excluir_usuario(id: str):
        identificador = validar(EsquemaParametroId, {"id": id}).id
        deps.excluir_usuario.executar(identificador)
        return "", 204
