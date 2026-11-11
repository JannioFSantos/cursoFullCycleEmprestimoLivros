"""Pacote da aplicação.

O ponto de entrada é a fábrica `criar_app`, em `app/fabrica.py`. Ela existe
para que os testes possam montar a aplicação com um banco e um relógio
controlados, sem abrir uma porta de rede.
"""

from app.fabrica import criar_app

# Flask descobre a fábrica pelo nome `create_app` ao rodar `flask --app app`.
create_app = criar_app

__all__ = ["criar_app", "create_app"]
