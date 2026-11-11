"""Criação do blueprint da API e registro das rotas."""

from __future__ import annotations

from flask import Blueprint

from app.http.dependencias import Dependencias
from app.http.rotas_emprestimos import registrar_rotas_de_emprestimos
from app.http.rotas_infra import registrar_infraestrutura_na_api
from app.http.rotas_livros import registrar_rotas_de_livros
from app.http.rotas_usuarios import registrar_rotas_de_usuarios


def criar_api(deps: Dependencias) -> Blueprint:
    bp = Blueprint("api", __name__, url_prefix="/API")

    registrar_infraestrutura_na_api(bp, deps)
    registrar_rotas_de_livros(bp, deps)
    registrar_rotas_de_usuarios(bp, deps)
    registrar_rotas_de_emprestimos(bp, deps)

    return bp
