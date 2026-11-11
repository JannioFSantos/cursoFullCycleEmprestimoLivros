"""Rotas de infraestrutura: saúde, métricas e índice da API.

Elas são registradas duas vezes: na raiz (para o Coolify) e dentro de /API
(para ficar junto do contrato).
"""

from __future__ import annotations

import time

from flask import Blueprint, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.http.dependencias import Dependencias

INICIO_DO_PROCESSO = time.monotonic()


def _health(deps: Dependencias) -> tuple[Response, int] | dict[str, object]:
    try:
        # Não basta o processo estar vivo: a API só é útil se o banco responde.
        with deps.engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "uptimeSegundos": round(time.monotonic() - INICIO_DO_PROCESSO),
        }
    except Exception:  # noqa: BLE001 - qualquer falha vira 503
        return (
            jsonify({"status": "degradado", "banco": "indisponivel"}),
            503,
        )


def _metrics(deps: Dependencias) -> Response:
    return Response(
        generate_latest(deps.registro),
        mimetype=CONTENT_TYPE_LATEST,
    )


def registrar_infraestrutura_na_raiz(app, deps: Dependencias) -> None:
    @app.get("/health", endpoint="health_raiz")
    def health_raiz():
        return _health(deps)

    @app.get("/metrics", endpoint="metrics_raiz")
    def metrics_raiz():
        return _metrics(deps)


def registrar_infraestrutura_na_api(bp: Blueprint, deps: Dependencias) -> None:
    @bp.get("/health")
    def health_api():
        return _health(deps)

    @bp.get("/metrics")
    def metrics_api():
        return _metrics(deps)

    @bp.get("")
    def indice_da_api():
        return jsonify(
            {
                "nome": "API de Empréstimos de Biblioteca",
                "nivel": "Projeto B — Full Cycle (Python/Flask)",
                "documentacao": "/API/docs",
                "openapi": "/API/openapi.yaml",
                "tela": "/",
                "rotas": [
                    "GET /API/health",
                    "GET /API/metrics",
                    "GET /API/docs",
                    "POST /API/livros",
                    "GET /API/livros",
                    "PUT /API/livros/:id",
                    "DELETE /API/livros/:id",
                    "POST /API/usuarios",
                    "GET /API/usuarios",
                    "GET /API/usuarios/:id",
                    "PUT /API/usuarios/:id",
                    "DELETE /API/usuarios/:id",
                    "POST /API/emprestimos",
                    "GET /API/emprestimos",
                    "PATCH /API/emprestimos/:id/devolucao",
                    "GET /API/emprestimos/atrasados",
                ],
            }
        )
