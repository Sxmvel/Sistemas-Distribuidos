def corpo_completo(livro, **sobrescritas):
    base = {
        "titulo": livro["titulo"],
        "autor": livro["autor"],
        "isbn": livro["isbn"],
        "ano": livro["ano"],
        "exemplares_total": livro["exemplares_total"],
    }
    base.update(sobrescritas)
    return base


def test_apos_delete_o_get_nunca_devolve_representacao(cliente, livro):
    cliente.delete(f"/v1/livros/{livro['id']}")

    assert cliente.get(f"/v1/livros/{livro['id']}").status_code == 404


def test_delete_repetido_mantem_o_mesmo_estado_final(cliente, livro):
    primeira = cliente.delete(f"/v1/livros/{livro['id']}")
    segunda = cliente.delete(f"/v1/livros/{livro['id']}")

    assert primeira.status_code == 204
    assert segunda.status_code == 404
    assert cliente.get(f"/v1/livros/{livro['id']}").status_code == 404


def test_put_identico_repetido_nao_altera_o_resultado(cliente, livro):
    novo = corpo_completo(livro, titulo="Título revisado")

    primeira = cliente.put(f"/v1/livros/{livro['id']}", json=novo)
    segunda = cliente.put(f"/v1/livros/{livro['id']}", json=novo)

    assert primeira.json() == segunda.json()
    assert primeira.headers["ETag"] == segunda.headers["ETag"]


def test_criacao_invalida_nunca_persiste_estado(cliente, dados_de_livro):
    antes = cliente.get("/v1/livros").json()["total"]

    cliente.post("/v1/livros", json=dados_de_livro(ano=99))

    assert cliente.get("/v1/livros").json()["total"] == antes


def test_post_repetido_cria_recursos_distintos(cliente, dados_de_livro):
    primeira = cliente.post("/v1/livros", json=dados_de_livro())
    segunda = cliente.post("/v1/livros", json=dados_de_livro())

    assert primeira.json()["id"] != segunda.json()["id"]


def test_get_com_if_none_match_atual_devolve_304(cliente, livro):
    etag = cliente.get(f"/v1/livros/{livro['id']}").headers["ETag"]

    resposta = cliente.get(f"/v1/livros/{livro['id']}", headers={"If-None-Match": etag})

    assert resposta.status_code == 304
    assert resposta.content == b""


def test_get_com_if_none_match_obsoleto_devolve_200(cliente, livro):
    cliente.patch(f"/v1/livros/{livro['id']}", json={"ano": 1900})

    resposta = cliente.get(f"/v1/livros/{livro['id']}", headers={"If-None-Match": '"1"'})

    assert resposta.status_code == 200


def test_put_com_if_match_obsoleto_devolve_412(cliente, livro):
    etag = cliente.get(f"/v1/livros/{livro['id']}").headers["ETag"]
    cliente.put(f"/v1/livros/{livro['id']}", json=corpo_completo(livro, titulo="Escrita do cliente B"))

    resposta = cliente.put(
        f"/v1/livros/{livro['id']}",
        json=corpo_completo(livro, titulo="Escrita do cliente A"),
        headers={"If-Match": etag},
    )

    assert resposta.status_code == 412
    assert cliente.get(f"/v1/livros/{livro['id']}").json()["titulo"] == "Escrita do cliente B"


def test_put_com_if_match_valido_grava(cliente, livro):
    etag = cliente.get(f"/v1/livros/{livro['id']}").headers["ETag"]

    resposta = cliente.put(
        f"/v1/livros/{livro['id']}",
        json=corpo_completo(livro, titulo="Escrita autorizada"),
        headers={"If-Match": etag},
    )

    assert resposta.status_code == 200
    assert resposta.headers["ETag"] != etag


def test_sem_if_match_a_ultima_escrita_sobrescreve(cliente, livro):
    cliente.put(f"/v1/livros/{livro['id']}", json=corpo_completo(livro, titulo="Escrita do cliente B"))
    cliente.put(f"/v1/livros/{livro['id']}", json=corpo_completo(livro, titulo="Escrita do cliente A"))

    assert cliente.get(f"/v1/livros/{livro['id']}").json()["titulo"] == "Escrita do cliente A"


def test_toda_resposta_carrega_identificador_de_correlacao(cliente, livro):
    resposta = cliente.get(f"/v1/livros/{livro['id']}")

    assert resposta.headers["X-Request-ID"]
    assert float(resposta.headers["X-Duracao-Ms"]) >= 0


def test_correlacao_enviada_pelo_cliente_e_preservada(cliente):
    resposta = cliente.get("/v1/saude", headers={"X-Request-ID": "rastreio-123"})

    assert resposta.headers["X-Request-ID"] == "rastreio-123"


def test_erros_usam_o_envelope_padronizado(cliente):
    resposta = cliente.get("/v1/livros/999999")

    assert resposta.headers["content-type"].startswith("application/problem+json")
    assert {"tipo", "titulo", "status", "detalhe", "instancia", "correlacao"} <= set(resposta.json())
