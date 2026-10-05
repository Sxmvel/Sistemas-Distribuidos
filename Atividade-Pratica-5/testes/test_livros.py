import pytest


def test_criar_livro_devolve_201_com_location(cliente, dados_de_livro):
    resposta = cliente.post("/v1/livros", json=dados_de_livro())

    assert resposta.status_code == 201
    assert resposta.headers["Location"] == f"/v1/livros/{resposta.json()['id']}"
    assert resposta.headers["ETag"] == '"1"'


def test_criar_livro_calcula_exemplares_disponiveis(cliente, dados_de_livro):
    resposta = cliente.post("/v1/livros", json=dados_de_livro(exemplares_total=5))

    assert resposta.json()["exemplares_disponiveis"] == 5


def test_isbn_duplicado_devolve_409(cliente, dados_de_livro):
    dados = dados_de_livro()
    cliente.post("/v1/livros", json=dados)

    resposta = cliente.post("/v1/livros", json=dados)

    assert resposta.status_code == 409
    assert resposta.json()["tipo"] == "conflito-de-estado"


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("ano", 99),
        ("ano", 3000),
        ("titulo", "X"),
        ("autor", ""),
        ("isbn", "abc-def-ghij"),
        ("exemplares_total", 0),
        ("exemplares_total", -3),
    ],
)
def test_entrada_invalida_devolve_422(cliente, dados_de_livro, campo, valor):
    resposta = cliente.post("/v1/livros", json=dados_de_livro(**{campo: valor}))

    assert resposta.status_code == 422
    assert resposta.json()["tipo"] == "entrada-invalida"


def test_campo_desconhecido_devolve_422(cliente, dados_de_livro):
    resposta = cliente.post("/v1/livros", json={**dados_de_livro(), "desconhecido": 1})

    assert resposta.status_code == 422


def test_obter_livro_inexistente_devolve_404(cliente):
    resposta = cliente.get("/v1/livros/999999")

    assert resposta.status_code == 404
    assert resposta.json()["tipo"] == "recurso-nao-encontrado"


def test_substituir_livro(cliente, livro, dados_de_livro):
    novos = dados_de_livro(titulo="Dom Casmurro (revisado)", isbn=livro["isbn"])

    resposta = cliente.put(f"/v1/livros/{livro['id']}", json=novos)

    assert resposta.status_code == 200
    assert resposta.json()["titulo"] == "Dom Casmurro (revisado)"
    assert resposta.json()["versao"] == livro["versao"] + 1


def test_atualizar_parcial_preserva_demais_campos(cliente, livro):
    resposta = cliente.patch(f"/v1/livros/{livro['id']}", json={"ano": 1900})

    assert resposta.status_code == 200
    assert resposta.json()["ano"] == 1900
    assert resposta.json()["titulo"] == livro["titulo"]


def test_patch_sem_campos_devolve_422(cliente, livro):
    resposta = cliente.patch(f"/v1/livros/{livro['id']}", json={})

    assert resposta.status_code == 422


def test_remover_livro_devolve_204(cliente, livro):
    resposta = cliente.delete(f"/v1/livros/{livro['id']}")

    assert resposta.status_code == 204
    assert resposta.content == b""


def test_listagem_pagina_e_conta_total(cliente, dados_de_livro):
    for indice in range(12):
        cliente.post("/v1/livros", json=dados_de_livro(titulo=f"Livro {indice}"))

    resposta = cliente.get("/v1/livros", params={"pagina": 2, "tamanho": 5})
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo["total"] == 12
    assert corpo["total_de_paginas"] == 3
    assert len(corpo["itens"]) == 5


def test_listagem_recusa_tamanho_acima_do_limite(cliente):
    resposta = cliente.get("/v1/livros", params={"tamanho": 9999})

    assert resposta.status_code == 422


def test_listagem_filtra_por_autor(cliente, dados_de_livro):
    cliente.post("/v1/livros", json=dados_de_livro(autor="Clarice Lispector"))
    cliente.post("/v1/livros", json=dados_de_livro(autor="Machado de Assis"))

    resposta = cliente.get("/v1/livros", params={"autor": "Clarice"})

    assert resposta.json()["total"] == 1
    assert resposta.json()["itens"][0]["autor"] == "Clarice Lispector"


def test_listagem_filtra_apenas_disponiveis(cliente, dados_de_livro):
    esgotado = cliente.post("/v1/livros", json=dados_de_livro(exemplares_total=1)).json()
    cliente.post("/v1/livros", json=dados_de_livro(exemplares_total=3))
    cliente.post(f"/v1/livros/{esgotado['id']}/emprestimos", json={"leitor": "Ana Ribeiro"})

    resposta = cliente.get("/v1/livros", params={"apenas_disponiveis": True})

    assert resposta.json()["total"] == 1
