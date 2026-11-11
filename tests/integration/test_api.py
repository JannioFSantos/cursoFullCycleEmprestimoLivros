"""Teste de integração da API (o obrigatório do Projeto B, e um pouco além).

Aqui nada é fake: a aplicação inteira roda com PostgreSQL real, passando por
HTTP -> rota -> caso de uso -> SQLAlchemy -> banco.

Usamos `app.test_client()` em vez de abrir uma porta: é o mesmo caminho de uma
requisição real, só sem rede. O equivalente ao Supertest/Fastify inject.

Todas as rotas de negócio começam com /API, igual à produção.

Pré-requisito: banco de pé (`docker compose up -d db`). ATENÇÃO: o teste limpa
as tabelas, nunca rode contra um banco com dados que você queira manter.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

SEQUENCIA = 0


def proximo_isbn() -> str:
    global SEQUENCIA
    SEQUENCIA += 1
    return f"978000000{SEQUENCIA:04d}"


@pytest.fixture()
def criar_livro(cliente):
    def criar(exemplares_total: int = 1):
        resposta = cliente.post(
            "/API/livros",
            json={
                "titulo": f"Livro {proximo_isbn()}",
                "autor": "Autor de teste",
                "isbn": proximo_isbn(),
                "exemplaresTotal": exemplares_total,
            },
        )
        assert resposta.status_code == 201, resposta.get_json()
        return resposta.get_json()

    return criar


@pytest.fixture()
def criar_usuario(cliente):
    def criar():
        global SEQUENCIA
        SEQUENCIA += 1
        resposta = cliente.post(
            "/API/usuarios",
            json={
                "nome": f"Usuário {SEQUENCIA}",
                "email": f"usuario-{SEQUENCIA}@exemplo.com",
            },
        )
        assert resposta.status_code == 201, resposta.get_json()
        return resposta.get_json()

    return criar


@pytest.fixture()
def emprestar(cliente):
    def executar(livro_id: str, usuario_id: str):
        return cliente.post(
            "/API/emprestimos",
            json={"livroId": livro_id, "usuarioId": usuario_id},
        )

    return executar


def test_serve_a_tela_de_demonstracao_na_raiz(cliente):
    resposta = cliente.get("/")

    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["Content-Type"]
    assert "Biblioteca" in resposta.get_data(as_text=True)
    assert "/API" in resposta.get_data(as_text=True)


def test_responde_200_no_healthcheck_quando_o_banco_esta_acessivel(cliente):
    # O healthcheck fica na raiz porque é o endereço que o Coolify usa.
    raiz = cliente.get("/health")
    assert raiz.status_code == 200
    assert raiz.get_json()["status"] == "ok"

    # E também dentro de /API, junto do resto do contrato.
    dentro_da_api = cliente.get("/API/health")
    assert dentro_da_api.status_code == 200


def test_publica_a_documentacao_swagger_em_api_docs(cliente):
    pagina = cliente.get("/API/docs/")

    assert pagina.status_code == 200
    assert "swagger" in pagina.get_data(as_text=True).lower()

    # /API/docs/json é o mesmo contrato, em JSON, que o Swagger UI carrega.
    contrato = cliente.get("/API/docs/json")

    assert contrato.status_code == 200
    assert contrato.get_json()["openapi"] == "3.1.0"

    # Quem digitava /docs continua chegando na documentação nova.
    antigo = cliente.get("/docs")
    assert antigo.status_code == 302
    assert antigo.headers["Location"] == "/API/docs"


def test_empresta_um_livro_e_calcula_a_data_prevista(
    criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(1)
    usuario = criar_usuario()

    resposta = emprestar(livro["id"], usuario["id"])

    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["livroId"] == livro["id"]
    assert dados["usuarioId"] == usuario["id"]
    assert dados["status"] == "ATIVO"
    assert dados["dataPrevista"] == "2026-01-19T00:00:00.000Z"


def test_lista_usuarios_e_emprestimos_detalhados_para_a_tela(
    cliente, criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(1)
    usuario = criar_usuario()
    emprestar(livro["id"], usuario["id"])

    usuarios = cliente.get("/API/usuarios")
    assert usuarios.status_code == 200
    itens = usuarios.get_json()["itens"]
    assert len(itens) == 1
    assert itens[0]["id"] == usuario["id"]
    assert itens[0]["nome"] == usuario["nome"]

    emprestimos = cliente.get("/API/emprestimos")
    assert emprestimos.status_code == 200
    itens = emprestimos.get_json()["itens"]
    assert len(itens) == 1
    assert itens[0]["status"] == "ATIVO"
    assert itens[0]["livro"]["id"] == livro["id"]
    assert itens[0]["usuario"]["id"] == usuario["id"]
    assert itens[0]["usuario"]["nome"] == usuario["nome"]


def test_recusa_o_segundo_emprestimo_quando_so_existe_um_exemplar(
    criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(1)
    primeiro = criar_usuario()
    segundo = criar_usuario()

    assert emprestar(livro["id"], primeiro["id"]).status_code == 201

    resposta = emprestar(livro["id"], segundo["id"])

    assert resposta.status_code == 409
    assert resposta.get_json()["erro"]["codigo"] == "LIVRO_INDISPONIVEL"


def test_devolve_o_livro_e_permite_um_novo_emprestimo(
    cliente, criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(1)
    usuario = criar_usuario()

    criado = emprestar(livro["id"], usuario["id"])
    emprestimo_id = criado.get_json()["id"]

    devolucao = cliente.patch(f"/API/emprestimos/{emprestimo_id}/devolucao")

    assert devolucao.status_code == 200
    assert devolucao.get_json()["status"] == "DEVOLVIDO"

    outro_usuario = criar_usuario()
    assert emprestar(livro["id"], outro_usuario["id"]).status_code == 201


def test_bloqueia_usuario_em_atraso_e_lista_o_emprestimo_em_atrasados(
    cliente, criar_livro, criar_usuario, emprestar, avancar_dias
):
    livro = criar_livro(1)
    outro_livro = criar_livro(1)
    usuario = criar_usuario()

    emprestar(livro["id"], usuario["id"])

    # "Viajamos" 30 dias no tempo: o empréstimo de 14 dias está atrasado.
    avancar_dias(30)

    tentativa = emprestar(outro_livro["id"], usuario["id"])
    assert tentativa.status_code == 409
    assert tentativa.get_json()["erro"]["codigo"] == "USUARIO_COM_ATRASO"

    atrasados = cliente.get("/API/emprestimos/atrasados")

    assert atrasados.status_code == 200
    itens = atrasados.get_json()["itens"]
    assert len(itens) == 1
    assert itens[0]["usuario"]["id"] == usuario["id"]
    assert itens[0]["livro"]["id"] == livro["id"]


def test_recusa_o_quarto_emprestimo_ativo_do_mesmo_usuario(
    criar_livro, criar_usuario, emprestar
):
    usuario = criar_usuario()

    for _ in range(3):
        livro = criar_livro(1)
        assert emprestar(livro["id"], usuario["id"]).status_code == 201

    quarto_livro = criar_livro(1)
    resposta = emprestar(quarto_livro["id"], usuario["id"])

    assert resposta.status_code == 409
    assert resposta.get_json()["erro"]["codigo"] == "LIMITE_ATINGIDO"


def test_retorna_404_para_livro_inexistente(criar_usuario, emprestar):
    usuario = criar_usuario()

    resposta = emprestar("00000000-0000-4000-8000-000000000000", usuario["id"])

    assert resposta.status_code == 404
    assert resposta.get_json()["erro"]["codigo"] == "LIVRO_NAO_ENCONTRADO"


def test_retorna_400_com_detalhes_quando_o_corpo_e_invalido(cliente):
    resposta = cliente.post(
        "/API/emprestimos",
        json={"livroId": "nao-e-uuid", "usuarioId": "tambem-nao"},
    )

    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_retorna_409_ao_cadastrar_isbn_repetido(cliente):
    payload = {
        "titulo": "Livro com ISBN fixo",
        "autor": "Autor de teste",
        "isbn": "9780000009999",
        "exemplaresTotal": 1,
    }

    primeiro = cliente.post("/API/livros", json=payload)
    assert primeiro.status_code == 201

    # O índice único do PostgreSQL estoura e o handler traduz para 409.
    repetido = cliente.post("/API/livros", json=payload)

    assert repetido.status_code == 409
    assert repetido.get_json()["erro"]["codigo"] == "VALOR_JA_CADASTRADO"


def test_edita_um_livro_com_put(cliente, criar_livro):
    livro = criar_livro(2)

    resposta = cliente.put(
        f"/API/livros/{livro['id']}",
        json={
            "titulo": "Livro editado",
            "autor": "Autor editado",
            "isbn": "9780000007777",
            "exemplaresTotal": 4,
        },
    )

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["id"] == livro["id"]
    assert dados["titulo"] == "Livro editado"
    assert dados["autor"] == "Autor editado"
    assert dados["isbn"] == "9780000007777"
    assert dados["exemplaresTotal"] == 4


def test_recusa_reduzir_exemplares_abaixo_dos_emprestimos_ativos(
    cliente, criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(2)
    primeiro = criar_usuario()
    segundo = criar_usuario()

    assert emprestar(livro["id"], primeiro["id"]).status_code == 201
    assert emprestar(livro["id"], segundo["id"]).status_code == 201

    resposta = cliente.put(
        f"/API/livros/{livro['id']}",
        json={
            "titulo": livro["titulo"],
            "autor": "Autor de teste",
            "isbn": "9780000008888",
            "exemplaresTotal": 1,
        },
    )

    assert resposta.status_code == 409
    assert (
        resposta.get_json()["erro"]["codigo"]
        == "EXEMPLARES_ABAIXO_DOS_EMPRESTIMOS"
    )


def test_exclui_livro_sem_emprestimos_e_preserva_o_historico_do_livro_com_emprestimo(
    cliente, criar_livro, criar_usuario, emprestar
):
    sem_emprestimo = criar_livro(1)

    excluido = cliente.delete(f"/API/livros/{sem_emprestimo['id']}")
    assert excluido.status_code == 204

    lista = cliente.get("/API/livros").get_json()["itens"]
    assert sem_emprestimo["id"] not in [item["id"] for item in lista]

    com_emprestimo = criar_livro(1)
    usuario = criar_usuario()
    emprestar(com_emprestimo["id"], usuario["id"])

    # Mesmo com histórico, a exclusão dá 204: o livro sai do catálogo e a
    # linha continua no banco para o histórico não ser perdido.
    preservado = cliente.delete(f"/API/livros/{com_emprestimo['id']}")
    assert preservado.status_code == 204

    catalogo = cliente.get("/API/livros").get_json()["itens"]
    assert com_emprestimo["id"] not in [item["id"] for item in catalogo]

    # O empréstimo continua listado, com o livro marcado como excluído.
    emprestimos = cliente.get("/API/emprestimos").get_json()["itens"]
    historico = next(
        item
        for item in emprestimos
        if item["livro"]["id"] == com_emprestimo["id"]
    )
    assert historico["livro"]["id"] == com_emprestimo["id"]
    assert historico["livro"]["titulo"] == com_emprestimo["titulo"]
    assert historico["livro"]["excluidoEm"] is not None

    # Livro excluído não recebe empréstimo novo e não pode ser editado de novo.
    outro_usuario = criar_usuario()
    novo_emprestimo = emprestar(com_emprestimo["id"], outro_usuario["id"])
    assert novo_emprestimo.status_code == 404
    assert novo_emprestimo.get_json()["erro"]["codigo"] == "LIVRO_NAO_ENCONTRADO"

    editar_excluido = cliente.put(
        f"/API/livros/{com_emprestimo['id']}",
        json={
            "titulo": "Tentativa",
            "autor": "Autor",
            "isbn": "9780000005555",
            "exemplaresTotal": 1,
        },
    )
    assert editar_excluido.status_code == 404

    excluir_de_novo = cliente.delete(f"/API/livros/{com_emprestimo['id']}")
    assert excluir_de_novo.status_code == 404


def test_edita_um_usuario_com_put(cliente, criar_usuario):
    usuario = criar_usuario()

    resposta = cliente.put(
        f"/API/usuarios/{usuario['id']}",
        json={"nome": "Nome editado", "email": "editado@exemplo.com"},
    )

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["id"] == usuario["id"]
    assert dados["nome"] == "Nome editado"
    assert dados["email"] == "editado@exemplo.com"


def test_exclui_usuario_sem_emprestimos_e_preserva_o_historico_do_usuario_com_emprestimo(
    cliente, criar_livro, criar_usuario, emprestar
):
    sem_emprestimo = criar_usuario()

    excluido = cliente.delete(f"/API/usuarios/{sem_emprestimo['id']}")
    assert excluido.status_code == 204

    lista = cliente.get("/API/usuarios").get_json()["itens"]
    assert sem_emprestimo["id"] not in [item["id"] for item in lista]

    livro = criar_livro(1)
    com_emprestimo = criar_usuario()
    emprestar(livro["id"], com_emprestimo["id"])

    preservado = cliente.delete(f"/API/usuarios/{com_emprestimo['id']}")
    assert preservado.status_code == 204

    usuarios = cliente.get("/API/usuarios").get_json()["itens"]
    assert com_emprestimo["id"] not in [item["id"] for item in usuarios]

    # Buscar pelo id também passa a dar 404.
    busca = cliente.get(f"/API/usuarios/{com_emprestimo['id']}")
    assert busca.status_code == 404

    # O histórico continua com o nome de quem pegou o livro.
    emprestimos = cliente.get("/API/emprestimos").get_json()["itens"]
    historico = next(
        item
        for item in emprestimos
        if item["usuario"]["id"] == com_emprestimo["id"]
    )
    assert historico["usuario"]["id"] == com_emprestimo["id"]
    assert historico["usuario"]["nome"] == com_emprestimo["nome"]
    assert historico["usuario"]["excluidoEm"] is not None

    # Usuário excluído não pega livro novo e não pode ser editado de novo.
    outro_livro = criar_livro(1)
    novo_emprestimo = emprestar(outro_livro["id"], com_emprestimo["id"])
    assert novo_emprestimo.status_code == 404
    assert (
        novo_emprestimo.get_json()["erro"]["codigo"] == "USUARIO_NAO_ENCONTRADO"
    )

    editar_excluido = cliente.put(
        f"/API/usuarios/{com_emprestimo['id']}",
        json={"nome": "Tentativa", "email": "tentativa@exemplo.com"},
    )
    assert editar_excluido.status_code == 404

    excluir_de_novo = cliente.delete(f"/API/usuarios/{com_emprestimo['id']}")
    assert excluir_de_novo.status_code == 404


def test_retorna_404_ao_editar_ou_excluir_recurso_inexistente(cliente):
    id_inexistente = str(uuid4())

    editar_livro = cliente.put(
        f"/API/livros/{id_inexistente}",
        json={
            "titulo": "Livro",
            "autor": "Autor",
            "isbn": "9780000006666",
            "exemplaresTotal": 1,
        },
    )
    assert editar_livro.status_code == 404

    excluir_livro = cliente.delete(f"/API/livros/{id_inexistente}")
    assert excluir_livro.status_code == 404

    editar_usuario = cliente.put(
        f"/API/usuarios/{id_inexistente}",
        json={"nome": "Nome", "email": "nome@exemplo.com"},
    )
    assert editar_usuario.status_code == 404

    excluir_usuario = cliente.delete(f"/API/usuarios/{id_inexistente}")
    assert excluir_usuario.status_code == 404


# ---------------------------------------------------------------------------
# A tela de demonstração também é testada de ponta a ponta
# ---------------------------------------------------------------------------


def test_tela_demo_cadastra_livro_usuario_e_empresta(
    cliente, criar_livro, criar_usuario
):
    livro = criar_livro(1)
    usuario = criar_usuario()

    resposta = cliente.post(
        "/emprestimos",
        data={"livro_id": livro["id"], "usuario_id": usuario["id"]},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    assert "Empréstimo registrado com sucesso." in pagina
    assert livro["titulo"] in pagina


def test_tela_demo_mostra_erro_de_regra_sem_estourar_500(
    cliente, criar_livro, criar_usuario, emprestar
):
    livro = criar_livro(1)
    usuario = criar_usuario()
    emprestar(livro["id"], usuario["id"])

    outro_usuario = criar_usuario()
    resposta = cliente.post(
        "/emprestimos",
        data={"livro_id": livro["id"], "usuario_id": outro_usuario["id"]},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    assert "Não há exemplar disponível" in resposta.get_data(as_text=True)
