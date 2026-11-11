"""Configuração de logs.

Em produção escrevemos uma linha JSON por evento, que é o formato que
ferramentas de log entendem. Em desenvolvimento usamos um formato legível no
terminal. Em teste o log fica desligado para não poluir a saída do pytest.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

CAMPOS_EXTRAS = (
    "requisicao_id",
    "metodo",
    "rota",
    "status",
    "duracao_ms",
    "sinal",
    "ambiente",
)


class FormatadorJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados: dict[str, Any] = {
            "hora": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "nivel": record.levelname.lower(),
            "msg": record.getMessage(),
        }

        # Nomes em camelCase para combinar com o restante da API.
        nomes = {
            "requisicao_id": "requisicaoId",
            "duracao_ms": "duracaoMs",
        }
        for campo in CAMPOS_EXTRAS:
            if hasattr(record, campo):
                dados[nomes.get(campo, campo)] = getattr(record, campo)

        if record.exc_info:
            dados["erro"] = self.formatException(record.exc_info)

        return json.dumps(dados, ensure_ascii=False)


def configurar_logs(ambiente: str, nivel: str) -> None:
    if ambiente == "test":
        logging.disable(logging.CRITICAL)
        return

    raiz = logging.getLogger()
    raiz.setLevel(nivel.upper())

    # Evita handlers duplicados quando a fábrica é chamada mais de uma vez
    # (por exemplo, em testes ou no reload do Flask).
    for handler in list(raiz.handlers):
        raiz.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if ambiente == "production":
        handler.setFormatter(FormatadorJSON())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
        )

    raiz.addHandler(handler)

    # O servidor de desenvolvimento do Flask tem log próprio; deixamos quieto.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
