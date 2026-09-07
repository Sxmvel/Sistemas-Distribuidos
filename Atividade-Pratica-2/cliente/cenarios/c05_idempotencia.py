from cliente.comum import criar_livro, livro_de_teste, requisitar

NOME = "C05 - Idempotência"
DESCRICAO = "Comparação entre POST, PUT e DELETE quanto ao efeito de repetir a mesma requisição."


def executar(coletor):
    dados_a = livro_de_teste(titulo="Sagarana (cenário 05)")
    dados_b = livro_de_teste(titulo="Sagarana (cenário 05)")

    primeira = requisitar("POST", "/v1/livros", json=dados_a)
    segunda = requisitar("POST", "/v1/livros", json=dados_b)
    coletor.registrar(
        NOME,
        "POST /v1/livros repetido (isbn diferente)",
        "ids distintos",
        "ids distintos" if primeira.json()["id"] != segunda.json()["id"] else "mesmo id",
        "POST não é idempotente por definição: cada chamada cria um recurso novo, com URI nova. "
        "É por isso que o servidor, e não o cliente, escolhe o identificador.",
    )

    livro, etag = criar_livro(titulo="Macunaíma (cenário 05)")
    livro_id = livro["id"]
    substituicao = {
        "titulo": "Macunaíma (revisado)",
        "autor": "Mário de Andrade",
        "isbn": livro["isbn"],
        "ano": 1928,
        "exemplares_total": 2,
    }

    primeira = requisitar("PUT", f"/v1/livros/{livro_id}", json=substituicao)
    segunda = requisitar("PUT", f"/v1/livros/{livro_id}", json=substituicao)
    coletor.registrar(
        NOME,
        f"PUT /v1/livros/{livro_id} idêntico duas vezes",
        200,
        segunda.status_code,
        "Ambas retornam 200 e o mesmo corpo: PUT substitui a representação inteira, "
        "então repetir leva ao mesmo estado final.",
    )
    coletor.registrar(
        NOME,
        f"ETag após o PUT repetido ({primeira.headers.get('ETag')} vs {segunda.headers.get('ETag')})",
        "ETag idêntico",
        "ETag idêntico" if primeira.headers.get("ETag") == segunda.headers.get("ETag") else "ETag mudou",
        "O repositório só incrementa a versão quando algum campo realmente muda. Sem isso, "
        "repetir um PUT idêntico alteraria o ETag e quebraria a idempotência observável.",
    )

    primeira = requisitar("DELETE", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"DELETE /v1/livros/{livro_id} (primeira vez)",
        204,
        primeira.status_code,
        "204 sem corpo: não há representação a devolver depois de remover o recurso.",
    )

    segunda = requisitar("DELETE", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"DELETE /v1/livros/{livro_id} (segunda vez)",
        404,
        segunda.status_code,
        "O efeito é idempotente (o recurso continua ausente), mas o status difere. "
        "Idempotência é uma propriedade do estado resultante, não da resposta.",
    )

    resposta = requisitar("GET", f"/v1/livros/{livro_id}")
    coletor.registrar(
        NOME,
        f"GET /v1/livros/{livro_id} após DELETE",
        404,
        resposta.status_code,
        "Invariante de contrato: depois de DELETE bem-sucedido, GET no mesmo URI nunca "
        "pode devolver representação.",
    )
