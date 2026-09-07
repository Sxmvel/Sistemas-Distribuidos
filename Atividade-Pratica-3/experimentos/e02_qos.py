import threading
import time

from experimentos.comum import (
    chaves_de_mensagem,
    encerrar_processo,
    esperar_ate,
    esperar_conexao,
    esperar_processo,
    ident,
    iniciar_broker,
    iniciar_processo,
    parar_broker,
    publicadas,
    recebidas,
)

CODIGO = "E02"
TITULO = "QoS 0 contra QoS 1 com o broker indisponivel"
PERGUNTA = "O QoS escolhido e suficiente para o requisito do dominio?"
MENSAGENS = 60
INTERVALO = 0.15
ESPERA_ATE_A_QUEDA = 2.5
DURACAO_DA_QUEDA = 3.0

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_PAINEL = "app.assinantes.painel_acervo"


def _derrubar_broker_em_paralelo():
    def rotina():
        time.sleep(ESPERA_ATE_A_QUEDA)
        parar_broker()
        time.sleep(DURACAO_DA_QUEDA)
        iniciar_broker()

    linha = threading.Thread(target=rotina, daemon=True)
    linha.start()
    return linha


def _rodada(qos, sessao_persistente):
    sufixo = f"qos{qos}"
    painel = ident(CODIGO, f"painel-{sufixo}")
    terminal = ident(CODIGO, f"term-{sufixo}")

    argumentos_do_painel = [
        "--id",
        painel,
        "--qos",
        qos,
        "--ate-mensagens",
        MENSAGENS,
        "--duracao",
        90,
    ]
    if sessao_persistente:
        argumentos_do_painel.append("--sessao-persistente")

    assinante = iniciar_processo(
        MODULO_DO_PAINEL, *argumentos_do_painel, identificador=painel
    )
    esperar_conexao(painel)

    interrupcao = _derrubar_broker_em_paralelo()
    publicador = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        qos,
        "--mensagens",
        MENSAGENS,
        "--intervalo",
        INTERVALO,
        "--semente",
        7,
        identificador=terminal,
    )

    esperar_processo(publicador, 180)
    interrupcao.join(30)
    esperar_ate(lambda: len(recebidas(painel)) >= MENSAGENS, 30)
    encerrar_processo(assinante)

    tentadas = publicadas(terminal, aceitas_apenas=False)
    aceitas = [evento for evento in tentadas if evento.get("aceito")]
    recusadas = [evento for evento in tentadas if not evento.get("aceito")]
    chaves_enviadas = {
        (evento["processo"], evento["sequence"]) for evento in tentadas
    }
    chaves_recebidas = chaves_de_mensagem(recebidas(painel))
    perdidas = chaves_enviadas - chaves_recebidas

    return {
        "qos": qos,
        "tentadas": len(tentadas),
        "aceitas": len(aceitas),
        "recusadas": len(recusadas),
        "recebidas": len(chaves_recebidas),
        "perdidas": len(perdidas),
    }


def executar(coletor):
    zero = _rodada(0, sessao_persistente=False)
    um = _rodada(1, sessao_persistente=True)

    coletor.registrar(
        CODIGO,
        "mensagens produzidas em cada rodada",
        MENSAGENS,
        zero["tentadas"],
        f"Mesma carga nas duas rodadas ({MENSAGENS} mensagens), com o broker parado "
        f"por {DURACAO_DA_QUEDA:.0f}s no meio.",
    )
    coletor.registrar(
        CODIGO,
        "QoS 0 recusadas pelo cliente (sem conexao)",
        "> 0",
        zero["recusadas"],
        "Sem conexao o publish de QoS 0 retorna NO_CONN e a mensagem e simplesmente descartada.",
        sucesso=zero["recusadas"] > 0,
    )
    coletor.registrar(
        CODIGO,
        "QoS 0 perdidas (produzidas e nunca recebidas)",
        "> 0",
        zero["perdidas"],
        "QoS 0 e no maximo uma vez: nao ha confirmacao nem reenvio, logo a queda vira perda.",
        sucesso=zero["perdidas"] > 0,
    )
    coletor.registrar(
        CODIGO,
        "QoS 1 perdidas (produzidas e nunca recebidas)",
        0,
        um["perdidas"],
        "QoS 1 e pelo menos uma vez: a mensagem fica na fila do cliente e e reenviada "
        "apos a reconexao.",
    )
    coletor.registrar(
        CODIGO,
        "QoS 1 recebidas pelo assinante",
        MENSAGENS,
        um["recebidas"],
        "A sessao persistente preserva a assinatura, entao o broker guarda o que chegou "
        "enquanto o assinante reconectava.",
    )
    coletor.registrar(
        CODIGO,
        "entrega de QoS 1 supera a de QoS 0",
        True,
        um["recebidas"] > zero["recebidas"],
        f"QoS 0 entregou {zero['recebidas']} de {MENSAGENS}; "
        f"QoS 1 entregou {um['recebidas']} de {MENSAGENS}.",
        sucesso=um["recebidas"] > zero["recebidas"],
    )
