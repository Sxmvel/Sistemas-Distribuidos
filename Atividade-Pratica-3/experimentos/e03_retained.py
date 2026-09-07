from app import config
from experimentos.comum import (
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    eventos,
    ident,
    iniciar_processo,
    recebidas,
)

CODIGO = "E03"
TITULO = "Retained como ultimo valor conhecido"
PERGUNTA = "Quando retained e apropriado e quando e perigoso?"
MOVIMENTACOES = 5

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_SERVICO = "app.assinantes.servico_atrasos"


def _observador(nome, filtros, duracao=15):
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


def executar(coletor):
    terminal = ident(CODIGO, "term-01")
    topico_de_status = f"biblioteca/central/{terminal}/status"
    topico_de_emprestimo = f"biblioteca/central/{terminal}/emprestimo"

    publicador = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        1,
        "--mensagens",
        MOVIMENTACOES,
        "--intervalo",
        0.05,
        "--semente",
        13,
        identificador=terminal,
    )
    esperar_processo(publicador, 60)

    tardio, processo_tardio = _observador("tardio", [topico_de_status])
    esperar_ate(lambda: len(eventos(tardio, "status-aplicado")) >= 1, 15)
    encerrar_processo(processo_tardio)

    movimentacoes, processo_movimentacoes = _observador(
        "tardio-mov", [topico_de_emprestimo], duracao=6
    )
    esperar_processo(processo_movimentacoes, 30)

    segundo, processo_segundo = _observador("tardio-2", [topico_de_status])
    esperar_ate(lambda: len(eventos(segundo, "status-aplicado")) >= 1, 15)
    encerrar_processo(processo_segundo)

    status = eventos(tardio, "status-aplicado")
    retidos = [evento for evento in status if evento.get("retain")]
    estados = [evento.get("estado") for evento in status]
    depois_do_fim = eventos(segundo, "status-aplicado")
    sem_retained = recebidas(movimentacoes)

    coletor.registrar(
        CODIGO,
        "assinante tardio recebeu o status retido",
        "> 0",
        len(retidos),
        "O broker guarda a ultima mensagem retained do topico e a entrega no ato da assinatura.",
        sucesso=len(retidos) > 0,
    )
    coletor.registrar(
        CODIGO,
        "recebeu apenas o ultimo estado, nao o historico",
        1,
        len(status),
        "O terminal publicou online e depois offline; o retained guarda so o ultimo valor.",
    )
    coletor.registrar(
        CODIGO,
        "estado entregue e o ultimo publicado",
        "['offline']",
        str(estados),
        "Retained serve para estado atual, nao para historico de transicoes.",
        sucesso=estados == ["offline"],
    )
    coletor.registrar(
        CODIGO,
        "movimentacoes nao chegam a quem assina depois",
        0,
        len(sem_retained),
        f"As {MOVIMENTACOES} movimentacoes foram publicadas sem retain: quem assina depois "
        "nao ve nada.",
    )
    coletor.registrar(
        CODIGO,
        "status continua sendo servido com o produtor morto",
        "> 0",
        len(depois_do_fim),
        "Risco do retained: o valor sobrevive ao produtor e pode ser lido como atual "
        "mesmo estando obsoleto.",
        sucesso=len(depois_do_fim) > 0,
    )
