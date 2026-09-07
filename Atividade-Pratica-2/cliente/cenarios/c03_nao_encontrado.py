from cliente.comum import requisitar

NOME = "C03 - Recurso inexistente"
DESCRICAO = "Toda referência a um recurso que não existe resulta em 404, inclusive em sub-recursos."

INEXISTENTE = 999999


def executar(coletor):
    resposta = requisitar("GET", f"/v1/livros/{INEXISTENTE}")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{INEXISTENTE}",
        404,
        resposta.status_code,
        "A URI é sintaticamente válida e o recurso simplesmente não existe. "
        f"O detalhe é específico e não vaza estrutura interna: {resposta.json()['detalhe']}",
    )

    resposta = requisitar("GET", f"/v1/emprestimos/{INEXISTENTE}")
    coletor.registrar(
        NOME,
        f"GET /v1/emprestimos/{INEXISTENTE}",
        404,
        resposta.status_code,
        "Empréstimo também é recurso de primeira classe, endereçável fora do livro pai.",
    )

    resposta = requisitar("GET", f"/v1/livros/{INEXISTENTE}/emprestimos")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{INEXISTENTE}/emprestimos",
        404,
        resposta.status_code,
        "Listar sub-recurso de pai inexistente é 404, não 200 com lista vazia: "
        "lista vazia afirmaria que o livro existe e não tem empréstimos.",
    )

    resposta = requisitar("POST", f"/v1/livros/{INEXISTENTE}/emprestimos", json={"leitor": "Ana Ribeiro"})
    coletor.registrar(
        NOME,
        f"POST /v1/livros/{INEXISTENTE}/emprestimos",
        404,
        resposta.status_code,
        "O corpo é válido, então não é 422: o que falha é a existência do pai referenciado na URI.",
    )

    resposta = requisitar("PUT", f"/v1/livros/{INEXISTENTE}", json={
        "titulo": "Qualquer", "autor": "Qualquer", "isbn": "9789999999999",
        "ano": 2020, "exemplares_total": 1,
    })
    coletor.registrar(
        NOME,
        f"PUT /v1/livros/{INEXISTENTE}",
        404,
        resposta.status_code,
        "Decisão de projeto: PUT não cria recurso em id escolhido pelo cliente, porque o id é "
        "gerado pelo servidor. Permitir criação por PUT abriria buracos na sequência de ids.",
    )

    resposta = requisitar("GET", "/v1/rota-que-nao-existe")
    coletor.registrar(
        NOME,
        "GET /v1/rota-que-nao-existe",
        404,
        resposta.status_code,
        "Até o 404 de rota desconhecida usa o mesmo envelope de erro, "
        "mantendo o contrato uniforme para o cliente.",
    )
