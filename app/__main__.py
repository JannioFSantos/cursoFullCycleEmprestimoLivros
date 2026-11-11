"""Ponto de entrada para desenvolvimento: `python -m app`.

Em produção usamos Gunicorn (ver `scripts/entrypoint.sh`). Este arquivo serve
para quem quer subir a API com reload automático enquanto desenvolve.
"""

from __future__ import annotations

from app import criar_app
from app.config import carregar_configuracao


def main() -> None:
    configuracao = carregar_configuracao()
    app = criar_app(configuracao)
    app.run(
        host=configuracao.host,
        port=configuracao.porta,
        debug=configuracao.ambiente == "development",
    )


if __name__ == "__main__":
    main()
