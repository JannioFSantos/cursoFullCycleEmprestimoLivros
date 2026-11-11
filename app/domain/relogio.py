"""Relógio = a única fonte de "agora" da aplicação.

Por que não chamar `datetime.now()` espalhado pelo código? Porque em teste
precisamos simular "hoje", por exemplo para provar que um empréstimo venceu.
Com este Protocol, o teste injeta um relógio controlado e o código de produção
usa o relógio real.

Detalhe importante: trabalhamos com `datetime` "naive" em UTC. O banco usa
`TIMESTAMP` sem fuso (como no projeto original) e toda a conta de datas é
feita em UTC, para não depender do fuso do servidor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Relogio(Protocol):
    def agora(self) -> datetime:
        """Retorna o instante atual em UTC, sem tzinfo."""
        ...


class RelogioDoSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)


relogio_do_sistema: Relogio = RelogioDoSistema()
