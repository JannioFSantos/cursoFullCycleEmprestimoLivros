"""Conversão das entidades Python para o JSON camelCase da API.

O contrato da API foi mantido igual ao da versão TypeScript: mesmos nomes de
campo, mesmas datas em ISO 8601 com milissegundos e `Z` no final.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.entidades import (
    Emprestimo,
    EmprestimoDetalhado,
    Livro,
    LivroComDisponibilidade,
    Usuario,
)


def data_iso(valor: datetime | None) -> str | None:
    """Formata como `2026-01-19T00:00:00.000Z` (UTC)."""
    if valor is None:
        return None
    return f"{valor:%Y-%m-%dT%H:%M:%S}.{valor.microsecond // 1000:03d}Z"


def serializar_livro(livro: Livro) -> dict[str, Any]:
    return {
        "id": str(livro.id),
        "titulo": livro.titulo,
        "autor": livro.autor,
        "isbn": livro.isbn,
        "exemplaresTotal": livro.exemplares_total,
        "criadoEm": data_iso(livro.criado_em),
        "excluidoEm": data_iso(livro.excluido_em),
    }


def serializar_livro_com_disponibilidade(
    livro: LivroComDisponibilidade,
) -> dict[str, Any]:
    dados = serializar_livro(livro)
    dados["emprestimosAtivos"] = livro.emprestimos_ativos
    dados["exemplaresDisponiveis"] = livro.exemplares_disponiveis
    return dados


def serializar_usuario(usuario: Usuario) -> dict[str, Any]:
    return {
        "id": str(usuario.id),
        "nome": usuario.nome,
        "email": usuario.email,
        "criadoEm": data_iso(usuario.criado_em),
        "excluidoEm": data_iso(usuario.excluido_em),
    }


def serializar_emprestimo(emprestimo: Emprestimo) -> dict[str, Any]:
    return {
        "id": str(emprestimo.id),
        "livroId": str(emprestimo.livro_id),
        "usuarioId": str(emprestimo.usuario_id),
        "status": emprestimo.status.value,
        "dataEmprestimo": data_iso(emprestimo.data_emprestimo),
        "dataPrevista": data_iso(emprestimo.data_prevista),
        "dataDevolucao": data_iso(emprestimo.data_devolucao),
    }


def serializar_emprestimo_detalhado(
    emprestimo: EmprestimoDetalhado,
) -> dict[str, Any]:
    dados = serializar_emprestimo(emprestimo)
    dados["livro"] = {
        "id": str(emprestimo.livro.id),
        "titulo": emprestimo.livro.titulo,
        "autor": emprestimo.livro.autor,
        "excluidoEm": data_iso(emprestimo.livro.excluido_em),
    }
    dados["usuario"] = {
        "id": str(emprestimo.usuario.id),
        "nome": emprestimo.usuario.nome,
        "email": emprestimo.usuario.email,
        "excluidoEm": data_iso(emprestimo.usuario.excluido_em),
    }
    return dados
