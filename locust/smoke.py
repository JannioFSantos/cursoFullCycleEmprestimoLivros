"""SMOKE TEST (Locust) — valida o fluxo principal uma única vez.

O que ele prova: a API sobe, aceita os dados, empresta, devolve e lista.
Se este teste falhar, não adianta rodar o teste de carga.

Rodar:

    docker compose up -d --build
    locust -f locust/smoke.py --headless -u 1 -r 1 -t 10s --only-summary

Ou apontando para o Coolify (repare no /API no final):

    BASE_URL=https://agendadeconsultas.v6.rocks/API \
      locust -f locust/smoke.py --headless -u 1 -r 1 -t 10s
"""

from __future__ import annotations

from comum import ClienteDaBiblioteca

from locust import constant, task


class Smoke(ClienteDaBiblioteca):
    abstract = False
    wait_time = constant(0)

    @task
    def fluxo_completo(self):
        livro = self.criar_livro(5, "smoke")
        usuario = self.criar_usuario("smoke")

        if livro and usuario:
            with self.emprestar(livro["id"], usuario["id"]) as resposta:
                if resposta.status_code == 201:
                    resposta.success()
                    emprestimo = resposta.json()

                    with self.devolver(emprestimo["id"]) as devolucao:
                        if (
                            devolucao.status_code == 200
                            and devolucao.json()["status"] == "DEVOLVIDO"
                        ):
                            devolucao.success()
                        else:
                            devolucao.failure(
                                f"devolução inesperada: {devolucao.status_code}"
                            )
                else:
                    resposta.failure(
                        f"empréstimo deveria dar 201, veio {resposta.status_code}"
                    )

            with self.client.get(
                "/emprestimos/atrasados",
                catch_response=True,
                name="/emprestimos/atrasados",
            ) as atrasados:
                if atrasados.status_code == 200:
                    atrasados.success()
                else:
                    atrasados.failure(
                        f"atrasados respondeu {atrasados.status_code}"
                    )

        # Um smoke test roda o fluxo UMA vez por usuário virtual.
        self.environment.runner.quit()
