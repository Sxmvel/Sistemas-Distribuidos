from cliente.comum import criar_livro, livro_de_teste, requisitar

NOME = "C04 - Conflito com o estado atual"
DESCRICAO = "Requisições válidas que colidem com o estado do recurso resultam em 409."


def executar(coletor):
    dados = livro_de_teste(titulo="Vidas Secas (cenário 04)", exemplares_total=1)
    requisitar("POST", "/v1/livros", json=dados)

    resposta = requisitar("POST", "/v1/livros", json=dados)
    coletor.registrar(
        NOME,
        "POST /v1/livros com isbn já cadastrado",
        409,
        resposta.status_code,
        "O isbn é UNIQUE no banco. O IntegrityError do SQLite é capturado no repositório e "
        "traduzido em erro de domínio: a mensagem técnica com nome de tabela nunca chega ao cliente.",
    )

    livro, _ = criar_livro(titulo="Iracema (cenário 04)", exemplares_total=1)
    livro_id = livro["id"]

    requisitar("POST", f"/v1/livros/{livro_id}/emprestimos", json={"leitor": "Bruno Tavares"})
    resposta = requisitar("POST", f"/v1/livros/{livro_id}/emprestimos", json={"leitor": "Carla Nunes"})
    coletor.registrar(
        NOME,
        f"POST /v1/livros/{livro_id}/emprestimos sem exemplar livre",
        409,
        resposta.status_code,
        "Regra de negócio verificada dentro da mesma transação que faria o INSERT, "
        "e não em uma consulta anterior solta: entre a checagem e a gravação nada muda.",
    )

    resposta = requisitar("DELETE", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"DELETE /v1/livros/{livro_id} com empréstimo ativo",
        409,
        resposta.status_code,
        "A regra vive no código do repositório, não numa constraint do banco: regra de negócio "
        "precisa estar visível onde se lê a operação.",
    )

    resposta = requisitar("GET", f"/v1/livros/{livro_id}/emprestimos")
    emprestimo_id = resposta.json()[0]["id"]

    requisitar("PATCH", f"/v1/emprestimos/{emprestimo_id}", json={"devolvido": True})
    resposta = requisitar("PATCH", f"/v1/emprestimos/{emprestimo_id}", json={"devolvido": True})
    coletor.registrar(
        NOME,
        f"PATCH /v1/emprestimos/{emprestimo_id} já devolvido",
        409,
        resposta.status_code,
        "Transição de estado inválida: devolver duas vezes não é erro de entrada, é conflito "
        "com o estado atual do recurso. Por isso 409 e não 422.",
    )

    resposta = requisitar("DELETE", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"DELETE /v1/livros/{livro_id} após devolução",
        204,
        resposta.status_code,
        "Devolvido o exemplar, o conflito desaparece e a mesma requisição que falhava passa: "
        "o 409 depende do estado, não da requisição.",
    )
