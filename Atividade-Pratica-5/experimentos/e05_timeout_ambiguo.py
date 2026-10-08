from cliente.resiliencia import requisitar
from experimentos.comum import Servidor, ident
from experimentos.proxy import ProxyDeFalhas

codigo = "E05"
titulo = "Timeout ambíguo: quatro causas, uma observação"
hipotese = (
    "Requisição perdida no canal, servidor lento, rede lenta e resposta perdida produzem a mesma observação no "
    "cliente: timeout de leitura aos 500 ms. Só o log do servidor separa parte dos casos, e nem ele separa "
    "todos."
)
falha_injetada = (
    "proxy TCP entre cliente e servidor nos modos perder-requisicao, atraso (1,2 s) e perder-resposta; "
    "atraso_ms=1200 no servidor"
)
classificacao = (
    "Omissão de recepção (requisição aceita pelo TCP e nunca processada), temporização no processo (servidor "
    "lento), temporização no canal (rede lenta) e omissão de envio no caminho de volta (resposta produzida e "
    "nunca entregue). Para o cliente, as quatro são ausência de resposta dentro do prazo."
)

timeout = 0.5


def executar(coletor):
    with Servidor(ident(codigo, "servidor")) as servidor, ProxyDeFalhas(servidor.porta) as proxy:
        destino = f"{proxy.url}/experimento/instavel"

        proxy.configurar("normal")
        referencia = coletor.anotar(codigo, "proxy normal", requisitar("GET", destino, timeout=timeout))
        coletor.registrar(
            codigo, "referência através do proxy", "sucesso", referencia.categoria,
            "O proxy, sozinho, não introduz falha.",
        )

        casos = []

        proxy.configurar("perder-requisicao")
        casos.append(("requisição perdida no canal", requisitar("GET", destino, timeout=timeout)))

        proxy.configurar("normal")
        casos.append(("servidor lento (1,2 s)", requisitar("GET", destino, timeout=timeout, params={"atraso_ms": 1200})))

        proxy.configurar("atraso", 1.2)
        casos.append(("rede lenta (1,2 s na volta)", requisitar("GET", destino, timeout=timeout)))

        proxy.configurar("perder-resposta")
        casos.append(("resposta perdida no canal", requisitar("GET", destino, timeout=timeout)))

        for nome, resultado in casos:
            coletor.anotar(codigo, nome, resultado)

        categorias = {resultado.categoria for _, resultado in casos}
        duracoes = [resultado.ultima.duracao_ms for _, resultado in casos]
        coletor.registrar(
            codigo,
            "observação do cliente nos quatro casos",
            "timeout-de-leitura",
            ", ".join(sorted(categorias)),
            f"Mesma categoria e mesma duração ({min(duracoes):.0f} a {max(duracoes):.0f} ms). Em todos os casos a "
            "conexão TCP foi aceita (pelo proxy), por isso não é timeout de conexão.",
            sucesso=categorias == {"timeout-de-leitura"},
        )

        vistos = {nome: servidor.esperar_eventos(resultado.correlacao, 1, limite=2.0) for nome, resultado in casos}

        perdida = vistos["requisição perdida no canal"]
        coletor.registrar(
            codigo,
            "requisição perdida: registro no servidor",
            "nenhum",
            "nenhum" if not perdida else f"{len(perdida)} registro(s)",
            "O servidor nunca soube da chamada. Para uma escrita, isso significa que o efeito não aconteceu, e "
            "repetir é seguro. O cliente, porém, não tem como saber que está neste caso.",
        )

        lento = vistos["servidor lento (1,2 s)"]
        coletor.registrar(
            codigo,
            "servidor lento: registro no servidor",
            "200 com duração >= 1200 ms",
            f"{lento[0]['status']} em {lento[0]['duracao_ms']:.0f} ms" if lento else "nenhum",
            "O servidor executou e demorou: a duração interna explica o timeout.",
            sucesso=bool(lento) and lento[0]["status"] == 200 and lento[0]["duracao_ms"] >= 1200,
        )

        rede = vistos["rede lenta (1,2 s na volta)"]
        resposta_perdida = vistos["resposta perdida no canal"]
        coletor.registrar(
            codigo,
            "rede lenta e resposta perdida: registro no servidor",
            "200 rápido nos dois",
            " / ".join(
                f"{eventos[0]['status']} em {eventos[0]['duracao_ms']:.1f} ms" if eventos else "nenhum"
                for eventos in (rede, resposta_perdida)
            ),
            "Nos dois casos o servidor respondeu em poucos milissegundos e registrou sucesso. Nem o log do servidor "
            "distingue a resposta que atrasou da que se perdeu: só quem observa o canal (aqui, o proxy) sabe.",
            sucesso=bool(rede) and bool(resposta_perdida)
            and rede[0]["status"] == resposta_perdida[0]["status"] == 200
            and rede[0]["duracao_ms"] < 100 and resposta_perdida[0]["duracao_ms"] < 100,
        )

        coletor.concluir(
            codigo,
            f"cliente: timeout-de-leitura nos quatro casos, entre {min(duracoes):.0f} e {max(duracoes):.0f} ms; "
            f"servidor: requisição perdida sem registro, servidor lento com 200 em "
            f"{lento[0]['duracao_ms'] if lento else 0:.0f} ms, rede lenta e resposta perdida com 200 em menos de 100 ms.",
            "Timeout não permite afirmar que o servidor falhou: em três dos quatro casos ele executou com sucesso. "
            "Rede lenta e resposta perdida são indistinguíveis até no log do servidor. Para escritas, só uma chave de "
            "idempotência torna o retry seguro sem saber qual caso ocorreu.",
        )
