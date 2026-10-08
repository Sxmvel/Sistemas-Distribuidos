import pytest

from testes.conftest import cabecalho_de


def test_escrita_sem_token_devolve_401_com_desafio(anonimo, dados_de_livro):
    resposta = anonimo.post("/v1/livros", json=dados_de_livro())

    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"].startswith("Bearer")
    assert resposta.json()["tipo"] == "nao-autenticado"


@pytest.mark.parametrize(
    "autorizacao",
    ["Bearer token-que-nao-existe", "Basic dXN1YXJpbzpzZW5oYQ==", "Bearer", "lab-bibliotecario-troque-me"],
)
def test_credencial_invalida_devolve_401(anonimo, dados_de_livro, autorizacao):
    resposta = anonimo.post("/v1/livros", json=dados_de_livro(), headers={"Authorization": autorizacao})

    assert resposta.status_code == 401


def test_papel_consulta_nao_cadastra_livro(anonimo, dados_de_livro):
    resposta = anonimo.post("/v1/livros", json=dados_de_livro(), headers=cabecalho_de("consulta"))

    assert resposta.status_code == 403
    assert resposta.json()["tipo"] == "sem-permissao"


def test_papel_atendente_nao_altera_acervo(anonimo, livro):
    resposta = anonimo.delete(f"/v1/livros/{livro['id']}", headers=cabecalho_de("atendente"))

    assert resposta.status_code == 403


def test_papel_atendente_registra_emprestimo_e_devolucao(anonimo, livro):
    emprestimo = anonimo.post(
        f"/v1/livros/{livro['id']}/emprestimos",
        json={"leitor": "Ana Ribeiro"},
        headers=cabecalho_de("atendente"),
    )
    devolucao = anonimo.patch(
        f"/v1/emprestimos/{emprestimo.json()['id']}",
        json={"devolvido": True},
        headers=cabecalho_de("atendente"),
    )

    assert emprestimo.status_code == 201
    assert devolucao.status_code == 200


def test_papel_consulta_nao_registra_emprestimo(anonimo, livro):
    resposta = anonimo.post(
        f"/v1/livros/{livro['id']}/emprestimos",
        json={"leitor": "Ana Ribeiro"},
        headers=cabecalho_de("consulta"),
    )

    assert resposta.status_code == 403


def test_leitura_continua_publica(anonimo, livro):
    assert anonimo.get(f"/v1/livros/{livro['id']}").status_code == 200
    assert anonimo.get("/v1/livros").status_code == 200


def test_campo_de_controle_nao_pode_ser_injetado(cliente, dados_de_livro):
    resposta = cliente.post("/v1/livros", json={**dados_de_livro(), "versao": 99})

    assert resposta.status_code == 422
