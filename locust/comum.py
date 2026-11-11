"""Funções compartilhadas pelos testes de carga com Locust.

O Locust substitui o k6 nesta versão Python: os cenários são escritos em
Python e o resultado sai no mesmo formato (requisições, p50/p95, falhas).
"""

from __future__ import annotations

import os
import time

from locust import HttpUser

# 127.0.0.1 em vez de localhost: no Windows, "localhost" pode tentar IPv6
# primeiro e adicionar ~2s por requisição — o que estragaria o teste de carga.
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000/API")


class ClienteDaBiblioteca(HttpUser):
    """Cliente HTTP já apontando para o prefixo /API e com JSON por padrão."""

    abstract = True
    host = BASE_URL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {"Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Apoio aos cenários
    # ------------------------------------------------------------------

    def criar_livro(self, exemplares_total: int, prefixo: str) -> dict:
        carimbo = time.time_ns()
        # ISBN aqui é só um identificador único de 13 dígitos (a API valida
        # tamanho, não o dígito verificador).
        isbn = f"978{carimbo % 10**10:010d}"
        with self.client.post(
            "/livros",
            json={
                "titulo": f"Livro {prefixo}-{isbn}",
                "autor": "Locust",
                "isbn": isbn,
                "exemplaresTotal": exemplares_total,
            },
            headers=self.headers,
            catch_response=True,
            name="/livros",
        ) as resposta:
            if resposta.status_code != 201:
                resposta.failure(
                    f"esperava 201, veio {resposta.status_code}: {resposta.text}"
                )
                return {}
            return resposta.json()

    def criar_usuario(self, prefixo: str) -> dict:
        sufixo = f"{prefixo}-{time.time_ns()}"
        with self.client.post(
            "/usuarios",
            json={
                "nome": f"Usuário {sufixo}",
                "email": f"{sufixo}@exemplo.com",
            },
            headers=self.headers,
            catch_response=True,
            name="/usuarios",
        ) as resposta:
            if resposta.status_code != 201:
                resposta.failure(
                    f"esperava 201, veio {resposta.status_code}: {resposta.text}"
                )
                return {}
            return resposta.json()

    def emprestar(self, livro_id: str, usuario_id: str):
        return self.client.post(
            "/emprestimos",
            json={"livroId": livro_id, "usuarioId": usuario_id},
            headers=self.headers,
            catch_response=True,
            name="/emprestimos",
        )

    def devolver(self, emprestimo_id: str):
        return self.client.patch(
            f"/emprestimos/{emprestimo_id}/devolucao",
            catch_response=True,
            name="/emprestimos/:id/devolucao",
        )
