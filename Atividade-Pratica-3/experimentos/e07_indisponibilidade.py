from app import config, topicos
from experimentos.comum import (
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    eventos,
    ident,
    iniciar_processo,
    publicadas,
    recebidas,
)

CODIGO = "E07"
TITULO = "Consumidor indisponivel: sessao persistente contra sessao efemera"
PERGUNTA = "O que acontece com o que foi produzido enquanto o consumidor estava fora?"
AQUECIMENTO = 5
MENSAGENS_OFFLINE = 60

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_SERVICO = "app.assinantes.servico_atrasos"

FILTROS = (topicos.FILTRO_DE_EMPRESTIMOS, topicos.FILTRO_DE_DEVOLUCOES)


def _assinante(nome, persistente, *, alvo=None, duracao=60, reiniciar_banco=False):
    identificador = ident(CODIGO, nome)
    argumentos = [
        "--id",
        identificador,
        "--qos",
        1,
        "--banco",
        str(config.RAIZ_DO_PROJETO / f"{CODIGO.lower()}-{nome}.db"),
        "--duracao",
        duracao,
    ]
    if not persistente:
        argumentos.append("--sessao-efemera")
    if reiniciar_banco:
        argumentos.append("--reiniciar-banco")
    if alvo:
        argumentos += ["--ate-mensagens", alvo]
    for filtro in FILTROS:
        argumentos += ["--filtro", filtro]
    processo = iniciar_processo(
        MODULO_DO_SERVICO, *argumentos, identificador=identificador
    )
    esperar_conexao(identificador)
    return identificador, processo


def _publicar(nome, mensagens, semente):
    terminal = ident(CODIGO, nome)
    processo = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        1,
        "--mensagens",
        mensagens,
        "--intervalo",
        0.03,
        "--semente",
        semente,
        identificador=terminal,
    )
    esperar_processo(processo, 180)
    return terminal


def executar(coletor):
    persistente, processo_persistente = _assinante(
        "persistente", True, alvo=AQUECIMENTO, duracao=60, reiniciar_banco=True
    )
    efemera, processo_efemera = _assinante(
        "efemera", False, alvo=AQUECIMENTO, duracao=60, reiniciar_banco=True
    )

    _publicar("term-aquecimento", AQUECIMENTO, 41)
    esperar_ate(lambda: len(recebidas(persistente)) >= AQUECIMENTO, 40)
    esperar_ate(lambda: len(recebidas(efemera)) >= AQUECIMENTO, 40)

    aquecimento_persistente = len(recebidas(persistente))
    aquecimento_efemera = len(recebidas(efemera))

    encerrar_processo(processo_persistente)
    encerrar_processo(processo_efemera)

    terminal_offline = _publicar("term-offline", MENSAGENS_OFFLINE, 43)
    produzidas_offline = len(publicadas(terminal_offline, aceitas_apenas=False))

    _, processo_persistente = _assinante(
        "persistente", True, alvo=MENSAGENS_OFFLINE, duracao=90
    )
    _, processo_efemera = _assinante("efemera", False, duracao=20)

    esperar_ate(
        lambda: len(recebidas(persistente)) >= AQUECIMENTO + MENSAGENS_OFFLINE, 90
    )
    esperar_processo(processo_efemera, 60)
    encerrar_processo(processo_persistente)

    total_persistente = len(recebidas(persistente))
    total_efemera = len(recebidas(efemera))
    recuperadas = total_persistente - aquecimento_persistente
    perdidas_pela_efemera = total_efemera - aquecimento_efemera
    retomadas = [
        evento
        for evento in eventos(persistente, "conectado")
        if evento.get("sessao_retomada")
    ]

    coletor.registrar(
        CODIGO,
        "aquecimento recebido pelos dois assinantes",
        f"{AQUECIMENTO} e {AQUECIMENTO}",
        f"{aquecimento_persistente} e {aquecimento_efemera}",
        "Com os dois no ar, sessao persistente e efemera se comportam igual.",
        sucesso=aquecimento_persistente == AQUECIMENTO
        and aquecimento_efemera == AQUECIMENTO,
    )
    coletor.registrar(
        CODIGO,
        "mensagens produzidas com os consumidores fora",
        MENSAGENS_OFFLINE,
        produzidas_offline,
        "O publicador nao sabe nem se importa que nenhum consumidor esteja no ar.",
    )
    coletor.registrar(
        CODIGO,
        "sessao persistente recuperou o que perdeu",
        MENSAGENS_OFFLINE,
        recuperadas,
        "Com clean_start=False e expiracao de sessao, o broker guardou a assinatura e a fila.",
    )
    coletor.registrar(
        CODIGO,
        "sessao efemera nao recuperou nada",
        0,
        perdidas_pela_efemera,
        "Com clean_start=True a sessao morre no disconnect: sem assinatura, nao ha fila.",
    )
    coletor.registrar(
        CODIGO,
        "broker confirmou a retomada da sessao",
        True,
        len(retomadas) > 0,
        "O CONNACK trouxe session_present=1, provando que o estado ficou no broker.",
        sucesso=len(retomadas) > 0,
    )
    coletor.registrar(
        CODIGO,
        "desacoplamento temporal tem custo de estado",
        True,
        f"{recuperadas} mensagens ficaram na fila do broker",
        "O broker passou a guardar estado por consumidor, o que exige limite de expiracao "
        "para nao crescer sem fim.",
        sucesso=recuperadas > 0,
    )
