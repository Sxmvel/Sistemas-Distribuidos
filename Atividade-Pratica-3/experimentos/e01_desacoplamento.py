from app import config, topicos
from experimentos.comum import (
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    ident,
    iniciar_processo,
    publicadas,
    recebidas,
    status_recebidos,
)

CODIGO = "E01"
TITULO = "Desacoplamento e roteamento por tópicos"
PERGUNTA = "O que exatamente foi desacoplado pelo broker?"
MENSAGENS_POR_TERMINAL = 30
TOTAL = MENSAGENS_POR_TERMINAL * 2

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_PAINEL = "app.assinantes.painel_acervo"
MODULO_DO_SERVICO = "app.assinantes.servico_atrasos"

TERMOS_PROIBIDOS = ("painel", "atrasos", "subscriber", "assinante")


def _publicador_ignora_consumidores():
    fonte = (config.RAIZ_DO_PROJETO / "app" / "publicadores" / "terminal.py").read_text(
        encoding="utf-8"
    )
    minusculo = fonte.lower()
    return [termo for termo in TERMOS_PROIBIDOS if termo in minusculo]


def executar(coletor):
    painel = ident(CODIGO, "painel")
    servico = ident(CODIGO, "atrasos")
    terminal_central = ident(CODIGO, "term-01")
    terminal_anexo = ident(CODIGO, "term-03")

    processos = [
        iniciar_processo(
            MODULO_DO_PAINEL,
            "--id",
            painel,
            "--qos",
            1,
            "--ate-mensagens",
            TOTAL,
            "--duracao",
            60,
            identificador=painel,
        ),
        iniciar_processo(
            MODULO_DO_SERVICO,
            "--id",
            servico,
            "--qos",
            1,
            "--reiniciar-banco",
            "--banco",
            str(config.RAIZ_DO_PROJETO / f"{CODIGO.lower()}-atrasos.db"),
            "--duracao",
            60,
            identificador=servico,
        ),
    ]
    esperar_conexao(painel)
    esperar_conexao(servico)

    publicadores = [
        iniciar_processo(
            MODULO_DO_PUBLICADOR,
            "--unidade",
            "central",
            "--terminal",
            terminal_central,
            "--qos",
            1,
            "--mensagens",
            MENSAGENS_POR_TERMINAL,
            "--intervalo",
            0.05,
            "--semente",
            11,
            identificador=terminal_central,
        ),
        iniciar_processo(
            MODULO_DO_PUBLICADOR,
            "--unidade",
            "anexo",
            "--terminal",
            terminal_anexo,
            "--qos",
            1,
            "--mensagens",
            MENSAGENS_POR_TERMINAL,
            "--intervalo",
            0.05,
            "--semente",
            29,
            identificador=terminal_anexo,
        ),
    ]
    for processo in publicadores:
        esperar_processo(processo, 90)

    esperar_ate(lambda: len(recebidas(painel)) >= TOTAL, 30)
    esperar_ate(lambda: len(recebidas(servico)) >= TOTAL, 30)

    for processo in processos:
        encerrar_processo(processo)

    enviadas = len(publicadas(terminal_central)) + len(publicadas(terminal_anexo))
    no_painel = recebidas(painel)
    no_servico = recebidas(servico)
    status_no_painel = [
        evento for evento in no_painel if evento.get("tipo") == topicos.STATUS
    ]
    status_no_servico = status_recebidos(servico)
    unidades = {
        evento["topico"].split("/")[1] for evento in no_painel if evento.get("topico")
    }
    termos = _publicador_ignora_consumidores()

    coletor.registrar(
        CODIGO,
        "movimentacoes publicadas pelos dois terminais",
        TOTAL,
        enviadas,
        f"{MENSAGENS_POR_TERMINAL} de cada terminal, em unidades diferentes.",
    )
    coletor.registrar(
        CODIGO,
        "painel-acervo recebeu todas as movimentacoes",
        TOTAL,
        len(no_painel),
        "Fan-out: cada assinante recebe a mensagem inteira, sem competir com o outro.",
    )
    coletor.registrar(
        CODIGO,
        "servico-atrasos recebeu todas as movimentacoes",
        TOTAL,
        len(no_servico),
        "Dois consumidores independentes leem o mesmo fluxo sem se conhecerem.",
    )
    coletor.registrar(
        CODIGO,
        "painel nao recebeu eventos de status",
        0,
        len(status_no_painel),
        "O filtro biblioteca/+/+/emprestimo exclui status: o roteamento e feito pelo topico.",
    )
    coletor.registrar(
        CODIGO,
        "servico-atrasos recebeu status (filtro biblioteca/#)",
        True,
        len(status_no_servico) > 0,
        "O wildcard # cobre os niveis restantes e alcanca os topicos de status.",
        sucesso=len(status_no_servico) > 0,
    )
    coletor.registrar(
        CODIGO,
        "painel enxergou as duas unidades",
        "{'anexo', 'central'}",
        str(set(sorted(unidades))),
        "O nivel de unidade no topico permite agregar sem o publicador saber quem le.",
        sucesso=unidades == {"central", "anexo"},
    )
    coletor.registrar(
        CODIGO,
        "codigo do publicador nao cita consumidor algum",
        [],
        termos,
        "Desacoplamento espacial: o publicador conhece o broker e o topico, nao o consumidor.",
        sucesso=not termos,
    )
