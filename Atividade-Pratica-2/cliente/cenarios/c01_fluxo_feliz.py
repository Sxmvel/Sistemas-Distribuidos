from cliente.comum import criar_livro, livro_de_teste, requisitar

NOME = "C01 - Fluxo feliz"
DESCRICAO = "Percurso completo de criação, leitura, empréstimo e devolução."


def executar(coletor):
    dados = livro_de_teste(titulo="O Cortiço (cenário 01)", exemplares_total=2)

    resposta = requisitar("POST", "/v1/livros", json=dados)
    coletor.registrar(
        NOME,
        "POST /v1/livros",
        201,
        resposta.status_code,
        "Criação devolve 201 e o cabeçalho Location aponta para o recurso novo, "
        f"evitando que o cliente monte URIs na mão: {resposta.headers.get('Location')}",
    )
    livro_id = resposta.json()["id"]

    resposta = requisitar("GET", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id}",
        200,
        resposta.status_code,
        f"A representação traz exemplares_disponiveis={resposta.json()['exemplares_disponiveis']}, "
        "campo derivado em consulta e não armazenado, portanto sempre coerente com os empréstimos.",
    )

    resposta = requisitar("POST", f"/v1/livros/{livro_id}/emprestimos", json={"leitor": "Ana Ribeiro"})
    coletor.registrar(
        NOME,
        f"POST /v1/livros/{livro_id}/emprestimos",
        201,
        resposta.status_code,
        "Sub-recurso criado sob o livro: a URI expressa a relação 1-para-N sem precisar de verbo no caminho.",
    )
    emprestimo_id = resposta.json()["id"]

    resposta = requisitar("GET", f"/v1/livros/{livro_id}/emprestimos")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id}/emprestimos",
        200,
        resposta.status_code,
        f"A coleção filtrada pelo pai retorna {len(resposta.json())} item(ns), sem exigir filtro do cliente.",
    )

    resposta = requisitar("PATCH", f"/v1/emprestimos/{emprestimo_id}", json={"devolvido": True})
    coletor.registrar(
        NOME,
        f"PATCH /v1/emprestimos/{emprestimo_id}",
        200,
        resposta.status_code,
        "A devolução é uma transição de estado do empréstimo, modelada como PATCH no recurso "
        "e não como POST /devolucao: o verbo fica no método HTTP, não na URI.",
    )

    resposta = requisitar("GET", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id} (após devolução)",
        200,
        resposta.status_code,
        f"exemplares_disponiveis voltou a {resposta.json()['exemplares_disponiveis']} "
        "automaticamente, porque o número é calculado e não mantido em coluna própria.",
    )
