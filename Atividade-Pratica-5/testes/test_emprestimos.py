def emprestar(cliente, livro_id, leitor="Ana Ribeiro"):
    return cliente.post(f"/v1/livros/{livro_id}/emprestimos", json={"leitor": leitor})


def test_registrar_emprestimo_devolve_201_com_location(cliente, livro):
    resposta = emprestar(cliente, livro["id"])

    assert resposta.status_code == 201
    assert resposta.headers["Location"] == f"/v1/emprestimos/{resposta.json()['id']}"
    assert resposta.json()["devolvido_em"] is None


def test_emprestimo_reduz_exemplares_disponiveis(cliente, livro):
    emprestar(cliente, livro["id"])

    resposta = cliente.get(f"/v1/livros/{livro['id']}")

    assert resposta.json()["exemplares_disponiveis"] == livro["exemplares_total"] - 1


def test_emprestimo_altera_a_versao_do_livro(cliente, livro):
    emprestar(cliente, livro["id"])

    resposta = cliente.get(f"/v1/livros/{livro['id']}")

    assert resposta.json()["versao"] == livro["versao"] + 1
    assert resposta.headers["ETag"] != '"1"'


def test_emprestimo_sem_exemplar_devolve_409(cliente, dados_de_livro):
    livro = cliente.post("/v1/livros", json=dados_de_livro(exemplares_total=1)).json()
    emprestar(cliente, livro["id"], "Ana Ribeiro")

    resposta = emprestar(cliente, livro["id"], "Bruno Tavares")

    assert resposta.status_code == 409
    assert resposta.json()["tipo"] == "conflito-de-estado"


def test_emprestimo_em_livro_inexistente_devolve_404(cliente):
    resposta = emprestar(cliente, 999999)

    assert resposta.status_code == 404


def test_listar_emprestimos_de_livro_inexistente_devolve_404(cliente):
    resposta = cliente.get("/v1/livros/999999/emprestimos")

    assert resposta.status_code == 404


def test_listar_emprestimos_do_livro(cliente, livro):
    emprestar(cliente, livro["id"], "Ana Ribeiro")
    emprestar(cliente, livro["id"], "Bruno Tavares")

    resposta = cliente.get(f"/v1/livros/{livro['id']}/emprestimos")

    assert resposta.status_code == 200
    assert [item["leitor"] for item in resposta.json()] == ["Ana Ribeiro", "Bruno Tavares"]


def test_devolucao_preenche_data(cliente, livro):
    emprestimo = emprestar(cliente, livro["id"]).json()

    resposta = cliente.patch(f"/v1/emprestimos/{emprestimo['id']}", json={"devolvido": True})

    assert resposta.status_code == 200
    assert resposta.json()["devolvido_em"] is not None


def test_devolucao_repetida_devolve_409(cliente, livro):
    emprestimo = emprestar(cliente, livro["id"]).json()
    cliente.patch(f"/v1/emprestimos/{emprestimo['id']}", json={"devolvido": True})

    resposta = cliente.patch(f"/v1/emprestimos/{emprestimo['id']}", json={"devolvido": True})

    assert resposta.status_code == 409


def test_reabrir_emprestimo_devolve_422(cliente, livro):
    emprestimo = emprestar(cliente, livro["id"]).json()

    resposta = cliente.patch(f"/v1/emprestimos/{emprestimo['id']}", json={"devolvido": False})

    assert resposta.status_code == 422


def test_remover_livro_com_emprestimo_ativo_devolve_409(cliente, livro):
    emprestar(cliente, livro["id"])

    resposta = cliente.delete(f"/v1/livros/{livro['id']}")

    assert resposta.status_code == 409


def test_remover_livro_apos_devolucao_funciona(cliente, livro):
    emprestimo = emprestar(cliente, livro["id"]).json()
    cliente.patch(f"/v1/emprestimos/{emprestimo['id']}", json={"devolvido": True})

    resposta = cliente.delete(f"/v1/livros/{livro['id']}")

    assert resposta.status_code == 204
