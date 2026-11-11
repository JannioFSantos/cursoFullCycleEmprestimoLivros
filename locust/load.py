"""TESTE DE CARGA (Locust) — mede o p95 sob concorrência.

Dois cenários ao mesmo tempo:

  - leitores: 2 usuários virtuais lendo GET /livros para cada 1 escritor;
  - escritores: criando empréstimos no MESMO livro, de propósito.

Por que todos no mesmo livro? Porque é o pior caso do `SELECT ... FOR UPDATE`:
as transações entram em fila. Separar leitura de escrita mostra qual das duas
está pior.

Rodar:

    locust -f locust/load.py --headless -u 30 -r 5 -t 1m --only-summary

O script se recusa a terminar com sucesso se o p95 furar o SLO declarado no
README (300 ms para leitura, 500 ms para escrita).
"""

from __future__ import annotations

import os
import random
import time

import requests
from comum import BASE_URL, ClienteDaBiblioteca

from locust import between, events, task

QUANTIDADE_DE_USUARIOS = int(os.getenv("CARGA_USUARIOS", "300"))
EXEMPLARES = int(os.getenv("CARGA_EXEMPLARES", "5000"))

# Preenchido no test_start. Cada worker do Locust cria o seu próprio cenário,
# o que aumenta a disputa — exatamente o que queremos medir.
DADOS: dict[str, object] = {"livro_id": None, "usuarios": []}

SLO_LEITURA_MS = 300
SLO_ESCRITA_MS = 500


@events.test_start.add_listener
def preparar_cenario(environment, **_):
    """Cria um livro com muitos exemplares e vários usuários de teste."""
    cabecalhos = {"Content-Type": "application/json"}
    sufixo = str(int(time.time() * 1000))

    livro = requests.post(
        f"{BASE_URL}/livros",
        json={
            "titulo": "Livro do teste de carga",
            "autor": "Locust",
            "isbn": f"carga-{sufixo}",
            "exemplaresTotal": EXEMPLARES,
        },
        headers=cabecalhos,
        timeout=30,
    )
    livro.raise_for_status()
    DADOS["livro_id"] = livro.json()["id"]

    usuarios = []
    for indice in range(QUANTIDADE_DE_USUARIOS):
        usuario = requests.post(
            f"{BASE_URL}/usuarios",
            json={
                "nome": f"Usuário de carga {indice}",
                "email": f"carga-{sufixo}-{indice}@exemplo.com",
            },
            headers=cabecalhos,
            timeout=30,
        )
        usuario.raise_for_status()
        usuarios.append(usuario.json()["id"])
    DADOS["usuarios"] = usuarios

    print(
        f"cenário pronto: livro {DADOS['livro_id']} com "
        f"{len(usuarios)} usuários"
    )


class Leitor(ClienteDaBiblioteca):
    abstract = False
    weight = 2
    wait_time = between(0.1, 0.5)

    @task
    def listar_livros(self):
        with self.client.get(
            "/livros", catch_response=True, name="/livros"
        ) as resposta:
            if resposta.status_code == 200:
                resposta.success()
            else:
                resposta.failure(f"GET /livros respondeu {resposta.status_code}")


class Escritor(ClienteDaBiblioteca):
    abstract = False
    weight = 1
    wait_time = between(0.1, 0.5)

    @task
    def criar_emprestimo(self):
        usuarios = DADOS["usuarios"] or []
        livro_id = DADOS["livro_id"]
        if not usuarios or not livro_id:
            return

        # Sorteia o usuário: depois de 3 empréstimos ativos ele recebe 409.
        # 409 aqui é a REGRA funcionando, não falha técnica.
        usuario_id = random.choice(usuarios)

        with self.emprestar(livro_id, usuario_id) as resposta:
            if resposta.status_code in (201, 409):
                resposta.success()
            else:
                resposta.failure(
                    f"esperava 201 ou 409, veio {resposta.status_code}"
                )


def _p95(entry) -> float | None:
    if entry is None or entry.num_requests == 0:
        return None
    return entry.get_response_time_percentile(0.95)


@events.test_stop.add_listener
def verificar_slo(environment, **_):
    leitura = _p95(environment.stats.get("/livros", "GET"))
    escrita = _p95(environment.stats.get("/emprestimos", "POST"))

    print("\n=== SLO ===")
    for nome, valor, limite in (
        ("GET /livros", leitura, SLO_LEITURA_MS),
        ("POST /emprestimos", escrita, SLO_ESCRITA_MS),
    ):
        if valor is None:
            print(f"{nome}: sem amostras")
            environment.process_exit_code = 1
        else:
            situacao = "OK" if valor <= limite else "ESTOUROU"
            print(f"{nome}: p95 {valor:.2f} ms (limite {limite} ms) — {situacao}")
            if valor > limite:
                environment.process_exit_code = 1
