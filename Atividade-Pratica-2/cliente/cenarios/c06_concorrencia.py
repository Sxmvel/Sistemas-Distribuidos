from cliente.comum import criar_livro, requisitar

NOME = "C06 - Concorrência e cache condicional"
DESCRICAO = "Perda de atualização entre dois clientes, e como ETag com If-Match a impede."


def corpo(livro, titulo):
    return {
        "titulo": titulo,
        "autor": livro["autor"],
        "isbn": livro["isbn"],
        "ano": livro["ano"],
        "exemplares_total": livro["exemplares_total"],
    }


def executar(coletor):
    livro, _ = criar_livro(titulo="A Hora da Estrela (cenário 06)")
    livro_id = livro["id"]

    leitura = requisitar("GET", f"/v1/livros/{livro_id}")
    etag = leitura.headers.get("ETag")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id} devolve ETag",
        "ETag presente",
        "ETag presente" if etag else "ETag ausente",
        f"O cabeçalho veio como ETag: {etag}. Ele identifica a versão da representação e é "
        "derivado da coluna versao, incrementada a cada alteração real do recurso.",
    )

    resposta = requisitar("GET", f"/v1/livros/{livro_id}", headers={"If-None-Match": etag})
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id} com If-None-Match",
        304,
        resposta.status_code,
        f"Resposta sem corpo ({len(resposta.content)} bytes): o cliente já tem a versão atual. "
        "Economiza banda e deixa explícito que representação e recurso são coisas diferentes.",
    )

    requisitar("GET", f"/v1/livros/{livro_id}")
    requisitar("GET", f"/v1/livros/{livro_id}")

    requisitar("PUT", f"/v1/livros/{livro_id}", json=corpo(livro, "Título escrito pelo cliente B"))
    resposta = requisitar("PUT", f"/v1/livros/{livro_id}", json=corpo(livro, "Título escrito pelo cliente A"))
    final = requisitar("GET", f"/v1/livros/{livro_id}").json()["titulo"]
    coletor.registrar(
        NOME,
        "PUT concorrente SEM If-Match (dois clientes)",
        "última escrita vence",
        "última escrita vence" if "cliente A" in final else final,
        "Perda de atualização demonstrada: A e B leram a mesma versão, ambos gravaram com 200 "
        f"e a alteração de B sumiu sem aviso. Estado final: {final!r}.",
    )

    livro2, _ = criar_livro(titulo="Laços de Família (cenário 06)")
    livro2_id = livro2["id"]
    etag_compartilhado = requisitar("GET", f"/v1/livros/{livro2_id}").headers["ETag"]

    resposta_b = requisitar(
        "PUT",
        f"/v1/livros/{livro2_id}",
        json=corpo(livro2, "Título escrito pelo cliente B"),
        headers={"If-Match": etag_compartilhado},
    )
    coletor.registrar(
        NOME,
        f"PUT /v1/livros/{livro2_id} do cliente B com If-Match válido",
        200,
        resposta_b.status_code,
        f"B chegou primeiro com a versão correta e gravou. O ETag avançou para "
        f"{resposta_b.headers.get('ETag')}.",
    )

    resposta_a = requisitar(
        "PUT",
        f"/v1/livros/{livro2_id}",
        json=corpo(livro2, "Título escrito pelo cliente A"),
        headers={"If-Match": etag_compartilhado},
    )
    coletor.registrar(
        NOME,
        f"PUT /v1/livros/{livro2_id} do cliente A com If-Match obsoleto",
        412,
        resposta_a.status_code,
        "A escrita de A é recusada porque a precondição falhou. Nada foi sobrescrito: "
        "o mesmo cenário que perdeu dados sem If-Match agora falha alto e visivelmente.",
    )

    final2 = requisitar("GET", f"/v1/livros/{livro2_id}").json()["titulo"]
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro2_id} após o conflito",
        "escrita de B preservada",
        "escrita de B preservada" if "cliente B" in final2 else final2,
        "Controle de concorrência otimista: em vez de travar o recurso, o servidor detecta "
        "a colisão na hora da escrita e devolve a decisão ao cliente.",
    )
