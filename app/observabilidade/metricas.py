"""Métricas no formato Prometheus.

Escolhemos duas métricas enxutas, que respondem às perguntas do dia a dia:
 1. "a API está lenta?"         -> histograma de duração por rota
 2. "quantos empréstimos saem?" -> contador de criados x recusados

O Registry é criado POR APLICAÇÃO (e não global) para que os testes possam
montar várias instâncias sem o erro "metric already registered".
"""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import (
    CollectorRegistry,
    Counter,
    GCCollector,
    Histogram,
    PlatformCollector,
    ProcessCollector,
)


@dataclass
class Metricas:
    duracao_http: Histogram
    emprestimos: Counter


def criar_registro_de_metricas() -> CollectorRegistry:
    registro = CollectorRegistry()

    # Métricas de processo (CPU, memória, threads...). Ajudam a explicar
    # comportamentos estranhos sob carga.
    ProcessCollector(registry=registro)
    PlatformCollector(registry=registro)
    GCCollector(registry=registro)

    return registro


def criar_metricas(registro: CollectorRegistry) -> Metricas:
    duracao_http = Histogram(
        "http_request_duration_seconds",
        "Duração das requisições HTTP em segundos",
        labelnames=("metodo", "rota", "status"),
        # Buckets escolhidos em volta do nosso SLO (p95 < 300 ms).
        buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5),
        registry=registro,
    )

    emprestimos = Counter(
        "emprestimos_total",
        "Total de tentativas de empréstimo, separadas por resultado",
        labelnames=("resultado",),
        registry=registro,
    )

    return Metricas(duracao_http=duracao_http, emprestimos=emprestimos)
