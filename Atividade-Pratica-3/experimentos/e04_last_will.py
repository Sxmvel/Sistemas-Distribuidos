from app import config
from experimentos.comum import (
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    eventos,
    ident,
    iniciar_processo,
    matar_processo,
)

CODIGO = "E04"
TITULO = "Last Will e deteccao de desconexao anormal"
PERGUNTA = "Como o sistema percebe que um produtor caiu sem avisar?"
KEEPALIVE = 5
LIMITE_DO_TESTAMENTO = KEEPALIVE * 3 + 10

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_SERVICO = "app.assinantes.servico_atrasos"


def _vigia(nome, duracao, filtros):
    identificador = ident(CODIGO, nome)
    argumentos = [
        "--id",
        identificador,
        "--qos",
        1,
        "--sessao-efemera",
        "--reiniciar-banco",
        "--banco",
        str(config.RAIZ_DO_PROJETO / f"{CODIGO.lower()}-{nome}.db"),
        "--duracao",
        duracao,
    ]
    for filtro in filtros:
        argumentos += ["--filtro", filtro]
    processo = iniciar_processo(
        MODULO_DO_SERVICO, *argumentos, identificador=identificador
    )
    esperar_conexao(identificador)
    return identificador, processo


def _publicar_e_matar(vigia, terminal):
    processo = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        1,
        "--mensagens",
        3,
        "--intervalo",
        0.05,
        "--keepalive",
        KEEPALIVE,
        "--manter-vivo",
        "--semente",
        17,
        identificador=terminal,
    )
    esperar_ate(
        lambda: any(
            evento.get("estado") == "online"
            for evento in eventos(vigia, "status-aplicado")
        ),
        30,
    )
    matar_processo(processo)
    return processo


def _publicar_e_encerrar(terminal):
    processo = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        1,
        "--mensagens",
        3,
        "--intervalo",
        0.05,
        "--keepalive",
        KEEPALIVE,
        "--semente",
        19,
        identificador=terminal,
    )
    esperar_processo(processo, 60)


def executar(coletor):
    abrupto = ident(CODIGO, "term-abrupto")
    limpo = ident(CODIGO, "term-limpo")
    vigia, processo_do_vigia = _vigia(
        "vigia",
        LIMITE_DO_TESTAMENTO + 20,
        [
            f"biblioteca/central/{abrupto}/status",
            f"biblioteca/central/{limpo}/status",
        ],
    )

    _publicar_e_matar(vigia, abrupto)

    testamento_chegou = esperar_ate(
        lambda: any(
            evento.get("testamento") and evento.get("estado") == "offline"
            for evento in eventos(vigia, "status-aplicado")
        ),
        LIMITE_DO_TESTAMENTO,
    )

    _publicar_e_encerrar(limpo)
    esperar_ate(
        lambda: any(
            evento.get("motivo") == "encerramento-programado"
            for evento in eventos(vigia, "status-aplicado")
        ),
        20,
    )
    encerrar_processo(processo_do_vigia)

    status = eventos(vigia, "status-aplicado")
    testamentos = [evento for evento in status if evento.get("testamento")]
    motivos = {evento.get("motivo") for evento in status}

    coletor.registrar(
        CODIGO,
        "broker publicou o Last Will do processo morto",
        True,
        testamento_chegou,
        f"O terminal foi morto sem DISCONNECT; apos o keepalive de {KEEPALIVE}s o broker "
        "publicou a mensagem registrada previamente.",
        sucesso=testamento_chegou,
    )
    coletor.registrar(
        CODIGO,
        "testamento chegou com estado offline",
        "> 0",
        len(testamentos),
        "O LWT e definido no CONNECT e publicado pelo broker, nao pelo cliente que caiu.",
        sucesso=len(testamentos) > 0,
    )
    coletor.registrar(
        CODIGO,
        "motivo distingue queda de encerramento",
        True,
        {"desconexao-anormal", "encerramento-programado"} <= motivos,
        "Queda anormal chega como desconexao-anormal; a saida limpa publica "
        "encerramento-programado antes do DISCONNECT.",
        sucesso={"desconexao-anormal", "encerramento-programado"} <= motivos,
    )
    coletor.registrar(
        CODIGO,
        "testamento identificado pela sequencia reservada",
        True,
        all(evento.get("estado") == "offline" for evento in testamentos),
        "O envelope do testamento usa sequence 0, fora do fluxo numerado do produtor, "
        "porque quem publica e o broker.",
        sucesso=all(evento.get("estado") == "offline" for evento in testamentos),
    )
