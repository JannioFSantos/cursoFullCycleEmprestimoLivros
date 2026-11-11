"""Erros de domínio.

`ErroDeDominio` significa que uma regra de negócio foi violada.

A vantagem de ter um erro próprio é que a camada HTTP não precisa "adivinhar"
o status: cada erro já carrega o código HTTP correto e um código de erro
estável (`LIVRO_INDISPONIVEL`, `USUARIO_COM_ATRASO`, ...) que o cliente da API
pode usar para tratar o caso.

Regra prática deste projeto:
  404 -> o recurso não existe
  409 -> o recurso existe, mas a operação conflita com uma regra
  400 -> os dados enviados estão inválidos
"""

from __future__ import annotations

from typing import Any


class ErroDeDominio(Exception):
    """Exceção de negócio com código estável e status HTTP."""

    def __init__(
        self,
        codigo: str,
        mensagem: str,
        status_code: int = 409,
        detalhes: Any | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.status_code = status_code
        self.detalhes = detalhes


class _Erros:
    """Fábrica de erros: centraliza as mensagens.

    Se amanhã uma mensagem mudar, muda só aqui. Em Python é comum usar funções
    de módulo, mas manter um objeto `erros` deixa o código dos casos de uso
    igual ao da versão TypeScript, o que ajuda na leitura do projeto.
    """

    @staticmethod
    def livro_nao_encontrado() -> ErroDeDominio:
        return ErroDeDominio(
            "LIVRO_NAO_ENCONTRADO", "Livro não encontrado.", 404
        )

    @staticmethod
    def usuario_nao_encontrado() -> ErroDeDominio:
        return ErroDeDominio(
            "USUARIO_NAO_ENCONTRADO", "Usuário não encontrado.", 404
        )

    @staticmethod
    def emprestimo_nao_encontrado() -> ErroDeDominio:
        return ErroDeDominio(
            "EMPRESTIMO_NAO_ENCONTRADO", "Empréstimo não encontrado.", 404
        )

    @staticmethod
    def livro_indisponivel() -> ErroDeDominio:
        return ErroDeDominio(
            "LIVRO_INDISPONIVEL",
            "Não há exemplar disponível para este livro.",
            409,
        )

    @staticmethod
    def usuario_com_atraso() -> ErroDeDominio:
        return ErroDeDominio(
            "USUARIO_COM_ATRASO",
            "O usuário possui empréstimo em atraso e não pode pegar outro livro.",
            409,
        )

    @staticmethod
    def limite_atingido(limite: int) -> ErroDeDominio:
        return ErroDeDominio(
            "LIMITE_ATINGIDO",
            f"O usuário já possui {limite} empréstimos ativos.",
            409,
        )

    @staticmethod
    def emprestimo_ja_devolvido() -> ErroDeDominio:
        return ErroDeDominio(
            "EMPRESTIMO_JA_DEVOLVIDO", "Este empréstimo já foi devolvido.", 409
        )

    @staticmethod
    def dados_invalidos(detalhes: Any) -> ErroDeDominio:
        return ErroDeDominio(
            "DADOS_INVALIDOS", "Dados da requisição inválidos.", 400, detalhes
        )

    @staticmethod
    def valor_ja_cadastrado(campo: str) -> ErroDeDominio:
        return ErroDeDominio(
            "VALOR_JA_CADASTRADO",
            f"Já existe um registro com este {campo}.",
            409,
        )

    @staticmethod
    def exemplares_abaixo_dos_emprestimos(
        exemplares_total: int, emprestimos_ativos: int
    ) -> ErroDeDominio:
        return ErroDeDominio(
            "EXEMPLARES_ABAIXO_DOS_EMPRESTIMOS",
            (
                f"O livro tem {emprestimos_ativos} empréstimo(s) ativo(s); "
                f"não é possível reduzir para {exemplares_total} exemplar(es)."
            ),
            409,
        )


erros = _Erros()
