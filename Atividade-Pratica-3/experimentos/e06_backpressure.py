from experimentos.comum import (
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    ident,
    iniciar_processo,
    publicadas,
    recebidas,
    resumo_de,
)

CODIGO = "E06"
TITULO = "Consumidor lento, atraso e backpressure"
PERGUNTA = "Onde a lentidao do consumidor aparece: em perda ou em atraso?"
MENSAGENS = 60
INTERVALO_DE_PRODUCAO = 0.01
ATRASO_DO_CONSUMIDOR = 0.08
LIMITE_DE_ATRASO_MS = 1000

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_PAINEL = "app.assinantes.painel_acervo"


def _painel(nome, atraso):
    identificador = ident(CODIGO, nome)
    processo = iniciar_processo(
        MODULO_DO_PAINEL,
        "--id",
        identificador,
        "--qos",
        1,
        "--lento",
        atraso,
        "--ate-mensagens",
        MENSAGENS,
        "--duracao",
        180,
        identificador=identificador,
    )
    esperar_conexao(identificador)
    return identificador, processo


def executar(coletor):
    lento, processo_lento = _painel("painel-lento", ATRASO_DO_CONSUMIDOR)
    rapido, processo_rapido = _painel("painel-rapido", 0.0)

    terminal = ident(CODIGO, "term-01")
    publicador = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        1,
        "--mensagens",
        MENSAGENS,
        "--intervalo",
        INTERVALO_DE_PRODUCAO,
        "--semente",
        31,
        identificador=terminal,
    )
    esperar_processo(publicador, 120)

    esperar_ate(lambda: len(recebidas(rapido)) >= MENSAGENS, 60)
    esperar_ate(lambda: len(recebidas(lento)) >= MENSAGENS, 120)
    encerrar_processo(processo_rapido)
    encerrar_processo(processo_lento)

    enviadas = len(publicadas(terminal, aceitas_apenas=False))
    no_lento = recebidas(lento)
    no_rapido = recebidas(rapido)
    resumo_lento = resumo_de(lento)
    resumo_rapido = resumo_de(rapido)
    atraso_do_lento = resumo_lento.get("atraso_maximo_ms", 0)
    atraso_do_rapido = resumo_rapido.get("atraso_maximo_ms", 0)
    atrasos = [
        evento["atraso_ms"] for evento in no_lento if evento.get("atraso_ms") is not None
    ]
    primeiro = atrasos[0] if atrasos else 0
    ultimo = atrasos[-1] if atrasos else 0

    coletor.registrar(
        CODIGO,
        "mensagens produzidas em rajada",
        MENSAGENS,
        enviadas,
        f"Producao a cada {INTERVALO_DE_PRODUCAO}s contra processamento de "
        f"{ATRASO_DO_CONSUMIDOR}s por mensagem.",
    )
    coletor.registrar(
        CODIGO,
        "consumidor lento recebeu tudo, sem perda",
        MENSAGENS,
        len(no_lento),
        "Com QoS 1 a lentidao do consumidor nao virou perda: virou fila e atraso.",
    )
    coletor.registrar(
        CODIGO,
        "consumidor rapido recebeu tudo",
        MENSAGENS,
        len(no_rapido),
        "O mesmo fluxo chegou completo ao consumidor rapido: o gargalo e do consumidor, "
        "nao do broker.",
    )
    coletor.registrar(
        CODIGO,
        "atraso maximo do consumidor lento",
        f"> {LIMITE_DE_ATRASO_MS} ms",
        f"{atraso_do_lento} ms",
        "O atraso cresce acumulando o tempo de processamento de cada mensagem da fila.",
        sucesso=atraso_do_lento > LIMITE_DE_ATRASO_MS,
    )
    coletor.registrar(
        CODIGO,
        "atraso do lento supera o do rapido",
        True,
        f"{atraso_do_lento} ms contra {atraso_do_rapido} ms",
        "Dois assinantes do mesmo topico com desempenho diferente: o fan-out entrega "
        "para os dois, cada um no seu ritmo.",
        sucesso=atraso_do_lento > atraso_do_rapido,
    )
    coletor.registrar(
        CODIGO,
        "atraso cresce da primeira para a ultima mensagem",
        True,
        f"{primeiro} ms para {ultimo} ms",
        "O crescimento monotono e a assinatura do backpressure: a fila drena mais devagar "
        "do que enche.",
        sucesso=ultimo > primeiro,
    )
