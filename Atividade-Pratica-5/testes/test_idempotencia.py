def emprestar(cliente, livro_id, leitor="Ana Ribeiro", chave=None):
    cabecalhos = {"Idempotency-Key": chave} if chave else {}
    return cliente.post(f"/v1/livros/{livro_id}/emprestimos", json={"leitor": leitor}, headers=cabecalhos)


def ativos(cliente, livro_id):
    return [item for item in cliente.get(f"/v1/livros/{livro_id}/emprestimos").json() if item["devolvido_em"] is None]


def test_sem_chave_a_repeticao_duplica_o_emprestimo(cliente, livro):
    emprestar(cliente, livro["id"])
    emprestar(cliente, livro["id"])

    assert len(ativos(cliente, livro["id"])) == 2


def test_mesma_chave_devolve_o_resultado_anterior(cliente, livro):
    primeira = emprestar(cliente, livro["id"], chave="chave-de-teste-01")
    segunda = emprestar(cliente, livro["id"], chave="chave-de-teste-01")

    assert primeira.status_code == segunda.status_code == 201
    assert primeira.json()["id"] == segunda.json()["id"]
    assert "Idempotent-Replayed" not in primeira.headers
    assert segunda.headers["Idempotent-Replayed"] == "true"
    assert len(ativos(cliente, livro["id"])) == 1


def test_mesma_chave_com_outro_pedido_devolve_422(cliente, livro):
    emprestar(cliente, livro["id"], "Ana Ribeiro", chave="chave-de-teste-02")

    resposta = emprestar(cliente, livro["id"], "Bruno Tavares", chave="chave-de-teste-02")

    assert resposta.status_code == 422
    assert resposta.json()["tipo"] == "chave-de-idempotencia-reutilizada"
    assert len(ativos(cliente, livro["id"])) == 1


def test_chave_nao_e_gravada_quando_o_efeito_falha(cliente, dados_de_livro):
    livro = cliente.post("/v1/livros", json=dados_de_livro(exemplares_total=1)).json()
    emprestar(cliente, livro["id"], "Ana Ribeiro")

    recusado = emprestar(cliente, livro["id"], "Bruno Tavares", chave="chave-de-teste-03")
    cliente.patch(f"/v1/emprestimos/{ativos(cliente, livro['id'])[0]['id']}", json={"devolvido": True})
    repetido = emprestar(cliente, livro["id"], "Bruno Tavares", chave="chave-de-teste-03")

    assert recusado.status_code == 409
    assert repetido.status_code == 201
    assert "Idempotent-Replayed" not in repetido.headers


def test_chave_curta_demais_devolve_422(cliente, livro):
    assert emprestar(cliente, livro["id"], chave="abc").status_code == 422
