from cliente.comum import livro_de_teste, requisitar

NOME = "C02 - Validação de entrada"
DESCRICAO = "Representações sintaticamente válidas mas semanticamente inválidas resultam em 422."


def executar(coletor):
    resposta = requisitar("POST", "/v1/livros", json=livro_de_teste(ano=99))
    coletor.registrar(
        NOME,
        "POST /v1/livros com ano=99",
        422,
        resposta.status_code,
        "O JSON é sintaticamente válido, então não é 400: o corpo foi entendido e reprovado "
        "na regra de domínio (ano entre 1450 e 2100). Esse é exatamente o caso do 422.",
    )

    resposta = requisitar("POST", "/v1/livros", json=livro_de_teste(titulo="X"))
    coletor.registrar(
        NOME,
        "POST /v1/livros com titulo de 1 caractere",
        422,
        resposta.status_code,
        "Restrição de tamanho mínimo declarada no esquema Pydantic, validada antes de qualquer "
        "acesso ao banco: a entrada inválida nunca chega a persistir estado.",
    )

    resposta = requisitar("POST", "/v1/livros", json=livro_de_teste(isbn="abc-def-ghij"))
    coletor.registrar(
        NOME,
        "POST /v1/livros com isbn fora do formato",
        422,
        resposta.status_code,
        "Validador de campo próprio: o isbn aceita apenas dígitos, hífen e X, com no mínimo "
        "10 dígitos. Validar no limite de confiança é o princípio da seção de segurança.",
    )

    resposta = requisitar("POST", "/v1/livros", json={**livro_de_teste(), "campo_inexistente": 1})
    coletor.registrar(
        NOME,
        "POST /v1/livros com campo desconhecido",
        422,
        resposta.status_code,
        "extra=forbid rejeita campos não previstos em vez de ignorá-los em silêncio, "
        "o que transforma erro de digitação do cliente em falha explícita.",
    )

    resposta = requisitar("GET", "/v1/livros", params={"tamanho": 9999})
    coletor.registrar(
        NOME,
        "GET /v1/livros?tamanho=9999",
        422,
        resposta.status_code,
        "O limite máximo de 100 itens por página protege memória e banda do servidor: "
        "listagem sem teto é o erro comum que a apostila aponta na seção de paginação.",
    )

    resposta = requisitar("PATCH", "/v1/livros/1", json={})
    coletor.registrar(
        NOME,
        "PATCH /v1/livros/1 com corpo vazio",
        422,
        resposta.status_code,
        "PATCH sem nenhum campo não tem significado: é rejeitado por um validador de modelo, "
        "não por uma checagem espalhada na rota.",
    )

    corpo = resposta.json()
    coletor.registrar(
        NOME,
        "Formato do corpo de erro (application/problem+json)",
        "campos presentes",
        "campos presentes" if {"tipo", "titulo", "status", "detalhe", "correlacao"} <= set(corpo) else corpo,
        "Todos os erros usam o mesmo envelope, com o identificador de correlação que também "
        "está no log: o cliente relata o id e o servidor acha a requisição exata.",
    )
