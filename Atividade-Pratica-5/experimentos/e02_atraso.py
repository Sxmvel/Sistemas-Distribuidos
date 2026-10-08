from cliente.resiliencia import chamar_com_retry, requisitar
from experimentos.comum import Servidor, ident

codigo = "E02"
titulo = "Atraso controlado no servidor"
hipotese = (
    "Um atraso de 800 ms, maior que o timeout de 500 ms, aparece no cliente como timeout de leitura, embora "
    "o servidor conclua a requisição com 200. Como o atraso é persistente, repetir não ajuda: cada retry é "
    "mais uma execução completa no servidor."
)
falha_injetada = "atraso_ms=300 e atraso_ms=800 na rota /experimento/instavel"
classificacao = (
    "Falha de temporização: o processo está correto, mas responde fora do intervalo que o cliente assumiu. "
    "Para o cliente, é indistinguível de omissão."
)

timeout = 0.5


def executar(coletor):
    with Servidor(ident(codigo, "servidor")) as servidor:
        destino = f"{servidor.url}/experimento/instavel"

        dentro = coletor.anotar(
            codigo, "atraso 300 ms, timeout 0,5 s", requisitar("GET", destino, timeout=timeout, params={"atraso_ms": 300})
        )
        coletor.registrar(
            codigo,
            "atraso menor que o timeout",
            "sucesso",
            dentro.categoria,
            f"Resposta em {dentro.ultima.duracao_ms:.0f} ms: lenta, mas dentro do limite. Lentidão só vira falha "
            "quando ultrapassa o que o cliente aceita esperar.",
        )

        fora = coletor.anotar(
            codigo, "atraso 800 ms, timeout 0,5 s", requisitar("GET", destino, timeout=timeout, params={"atraso_ms": 800})
        )
        coletor.registrar(
            codigo,
            "atraso maior que o timeout",
            "timeout-de-leitura",
            fora.categoria,
            f"O cliente desistiu em {fora.ultima.duracao_ms:.0f} ms. A conexão foi aceita e a requisição enviada; "
            "faltou apenas a resposta dentro do prazo.",
        )
        do_servidor = servidor.esperar_eventos(fora.correlacao, 1)
        coletor.registrar(
            codigo,
            "servidor concluiu a chamada que o cliente deu como perdida",
            200,
            do_servidor[0]["status"] if do_servidor else "sem registro",
            f"O log do servidor mostra status 200 em {do_servidor[0]['duracao_ms'] if do_servidor else '-'} ms para "
            "a mesma correlação. O timeout não provou falha: o servidor estava apenas lento.",
        )

        folgado = coletor.anotar(
            codigo, "atraso 800 ms, timeout 1,5 s", requisitar("GET", destino, timeout=1.5, params={"atraso_ms": 800})
        )
        coletor.registrar(
            codigo,
            "mesmo atraso com timeout maior",
            "sucesso",
            folgado.categoria,
            "Mesma condição do servidor, outro resultado: o que mudou foi só a decisão do cliente sobre quanto esperar.",
        )

        com_retry = coletor.anotar(
            codigo,
            "atraso 800 ms, timeout 0,5 s, 4 tentativas com backoff",
            chamar_com_retry("GET", destino, tentativas=4, timeout=timeout, params={"atraso_ms": 800}),
        )
        execucoes = servidor.esperar_eventos(com_retry.correlacao, 4)
        concluidas = [evento for evento in execucoes if evento["status"] == 200]
        coletor.registrar(
            codigo,
            "retry contra atraso persistente",
            "falha após 4 tentativas",
            "falha após 4 tentativas" if not com_retry.ok and len(com_retry.tentativas) == 4 else com_retry.categoria,
            "Todas as tentativas estouraram o timeout: o atraso não é transitório, então repetir não muda o resultado.",
        )
        coletor.registrar(
            codigo,
            "execuções completas no servidor durante o retry",
            4,
            len(concluidas),
            "O servidor concluiu com 200 as quatro execuções que o cliente contabilizou como falha. O retry "
            "quadruplicou o trabalho do servidor sem nenhum ganho para o cliente.",
        )

        coletor.concluir(
            codigo,
            f"300 ms -> sucesso em {dentro.ultima.duracao_ms:.0f} ms; 800 ms -> timeout em "
            f"{fora.ultima.duracao_ms:.0f} ms no cliente e 200 no log do servidor; 800 ms com timeout 1,5 s -> "
            f"sucesso; retry: {len(com_retry.tentativas)} timeouts no cliente, {len(concluidas)} execuções 200 no "
            f"servidor, {com_retry.duracao_total_ms / 1000:.1f} s até desistir.",
            "O timeout mede a paciência do cliente, não o estado do servidor. Contra atraso persistente, o retry "
            f"piorou o quadro: multiplicou por {len(concluidas)} a carga e adiou a desistência de 0,5 s para "
            f"{com_retry.duracao_total_ms / 1000:.1f} s.",
        )
