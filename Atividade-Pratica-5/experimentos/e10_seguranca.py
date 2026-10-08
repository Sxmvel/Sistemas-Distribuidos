from cliente.resiliencia import requisitar
from experimentos.comum import Servidor, cabecalho_de, ident, tokens
from experimentos.proxy import ProxyDeFalhas

codigo = "E10"
titulo = "Controle de segurança: token, autorização por papel e validação"
hipotese = (
    "Sem o controle, qualquer processo que alcance a porta altera o acervo. Com token Bearer e lista de papéis, "
    "escritas sem credencial válida recebem 401 e credenciais sem permissão recebem 403. O controle não protege "
    "o token em trânsito: em HTTP puro, quem observa o canal lê o token."
)
falha_injetada = (
    "requisições sem credencial, com credencial inválida, com papel insuficiente e com entrada maliciosa; escuta "
    "do canal por proxy"
)
classificacao = (
    "Ameaças de falsificação de identidade e elevação de privilégio, tratadas por autenticação (autenticidade) e "
    "autorização por papel. Ameaça residual: escuta do canal (confidencialidade), que exige TLS."
)


def livro_valido(numero):
    return {
        "titulo": f"Iracema ({numero})",
        "autor": "José de Alencar",
        "isbn": f"97885081{numero:05d}",
        "ano": 1865,
        "exemplares_total": 1,
    }


def executar(coletor):
    with Servidor(ident(codigo, "servidor")) as servidor:
        livros = f"{servidor.url}/v1/livros"
        casos = [
            ("POST /v1/livros sem Authorization", None, 401, "Sem credencial não há identidade: a escrita é recusada antes de tocar o domínio."),
            ("POST /v1/livros com token inexistente", {"Authorization": "Bearer chute-qualquer"}, 401, "Token desconhecido é tratado como ausência de identidade."),
            ("POST /v1/livros com esquema Basic", {"Authorization": "Basic YWRtaW46YWRtaW4="}, 401, "Só o esquema Bearer é aceito; outra forma de credencial não abre exceção."),
            ("POST /v1/livros com token padrão de desenvolvimento", {"Authorization": "Bearer lab-bibliotecario-troque-me"}, 401, "O laboratório injeta tokens gerados a cada execução, então o valor padrão do código não vale aqui."),
            ("POST /v1/livros com papel consulta", cabecalho_de("consulta"), 403, "Identidade válida, permissão insuficiente: 403, não 401. Autenticar não é autorizar."),
            ("POST /v1/livros com papel atendente", cabecalho_de("atendente"), 403, "O atendente registra empréstimos, mas não altera o acervo."),
            ("POST /v1/livros com papel bibliotecario", cabecalho_de("bibliotecario"), 201, "O único papel com permissão sobre o acervo."),
        ]
        criado = None
        for indice, (nome, cabecalhos, esperado, analise) in enumerate(casos):
            resultado = coletor.anotar(
                codigo, nome, requisitar("POST", livros, timeout=2.0, cabecalhos=cabecalhos, json=livro_valido(indice))
            )
            coletor.registrar(codigo, nome, esperado, resultado.status, analise)
            if resultado.status == 201:
                criado = resultado.resposta.json()
            if esperado == 401 and indice == 0:
                coletor.registrar(
                    codigo,
                    "401 traz o desafio WWW-Authenticate",
                    'Bearer realm="biblioteca"',
                    resultado.resposta.headers.get("WWW-Authenticate") if resultado.resposta is not None else "-",
                    "O servidor diz ao cliente qual esquema de autenticação espera, como manda a semântica do 401.",
                )

        emprestimo = coletor.anotar(
            codigo,
            "POST empréstimo com papel atendente",
            requisitar(
                "POST", f"{livros}/{criado['id']}/emprestimos", timeout=2.0,
                cabecalhos=cabecalho_de("atendente"), json={"leitor": "Ana Ribeiro"},
            ),
        )
        coletor.registrar(codigo, "atendente registra empréstimo", 201, emprestimo.status, "A lista de papéis concede ao atendente exatamente o que a função dele exige.")

        leitura = coletor.anotar(codigo, "GET sem token", requisitar("GET", f"{livros}/{criado['id']}", timeout=2.0))
        coletor.registrar(
            codigo,
            "leitura pública sem token",
            200,
            leitura.status,
            "Decisão de projeto: o catálogo é público. O controle protege integridade (quem altera), não a "
            "confidencialidade do acervo.",
        )

        entradas = [
            ("campo de controle injetado (versao=99)", {**livro_valido(101), "versao": 99}),
            ("título com 5000 caracteres", {**livro_valido(102), "titulo": "A" * 5000}),
            ("ano fora da faixa", {**livro_valido(103), "ano": -5}),
        ]
        for nome, corpo in entradas:
            resultado = coletor.anotar(
                codigo, nome, requisitar("POST", livros, timeout=2.0, cabecalhos=cabecalho_de("bibliotecario"), json=corpo)
            )
            coletor.registrar(
                codigo,
                f"validação robusta: {nome}",
                422,
                resultado.status,
                "O esquema recusa campos desconhecidos e limites violados mesmo para quem tem permissão: "
                "autorização não dispensa validação.",
            )

        abuso = coletor.anotar(
            codigo,
            "atraso_ms=600000 na rota de laboratório",
            requisitar("GET", f"{servidor.url}/experimento/instavel", timeout=2.0, params={"atraso_ms": 600000}),
        )
        coletor.registrar(
            codigo,
            "rota de laboratório limita o atraso pedido",
            422,
            abuso.status,
            "Sem o limite de 10 s, poucas requisições prenderiam todas as threads do servidor por 10 minutos: "
            "negação de serviço pela própria ferramenta de teste.",
        )

        registros = servidor.caminho_do_log.read_text(encoding="utf-8")
        saida = servidor.caminho_da_saida.read_text(encoding="utf-8") if servidor.caminho_da_saida.exists() else ""
        vazados = [papel for papel, token in tokens.items() if token in registros or token in saida]
        coletor.registrar(
            codigo,
            "tokens ausentes dos logs do servidor",
            "nenhum",
            ", ".join(vazados) or "nenhum",
            "O middleware registra método, caminho, status e correlação, nunca cabeçalhos. Log é um destino comum "
            "de vazamento de credencial.",
        )

        with ProxyDeFalhas(servidor.porta) as escuta:
            requisitar("GET", f"{escuta.url}/v1/livros/{criado['id']}", timeout=2.0, cabecalhos=cabecalho_de("bibliotecario"))
            capturado = bytes(escuta.capturado).decode("latin-1")
        coletor.registrar(
            codigo,
            "token legível por quem observa o canal HTTP",
            True,
            tokens["bibliotecario"] in capturado,
            "O proxy, no papel de intermediário na rede, leu o token do bibliotecário em texto claro. O controle "
            "por token depende de confidencialidade do canal: em uso real, TLS é pré-requisito, não opcional.",
            sucesso=tokens["bibliotecario"] in capturado,
        )

    with Servidor(ident(codigo, "sem-laboratorio"), laboratorio=False) as producao:
        desligada = coletor.anotar(
            codigo, "rota de laboratório com BIBLIOTECA_LABORATORIO=0",
            requisitar("GET", f"{producao.url}/experimento/instavel", timeout=2.0, params={"prob_falha": 1.0}),
        )
        coletor.registrar(
            codigo,
            "rota de injeção de falha desligada por padrão",
            404,
            desligada.status,
            "Fora do laboratório a rota não existe para o cliente. Endpoint de injeção de falha esquecido em "
            "produção é superfície de ataque.",
        )

    coletor.concluir(
        codigo,
        "sem credencial, credencial inválida, esquema Basic e token padrão -> 401; consulta e atendente no acervo "
        "-> 403; bibliotecário -> 201; atendente em empréstimo -> 201; leitura sem token -> 200; entradas "
        "maliciosas -> 422; tokens ausentes do log; token capturado em texto claro pelo proxy; rota de "
        "laboratório desligada -> 404.",
        "O controle tratou autenticidade (401 para quem não prova identidade) e autorização (403 para quem não tem "
        "permissão), preservando a integridade do acervo. Não tratou confidencialidade: em HTTP puro o token é "
        "legível por quem observa o canal, então a próxima camada necessária é TLS.",
    )
