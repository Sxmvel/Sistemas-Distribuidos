from app import config
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
    resumo_de,
)

CODIGO = "E05"
TITULO = "Duplicacao em QoS 2 e deduplicacao idempotente"
PERGUNTA = "Como o sistema identifica mensagem duplicada?"
MENSAGENS = 60
REENVIAR_A_CADA = 5
SEMENTE = 23
QOS = 2
ENTREGAS_ESPERADAS = MENSAGENS + MENSAGENS // REENVIAR_A_CADA

MODULO_DO_PUBLICADOR = "app.publicadores.terminal"
MODULO_DO_SERVICO = "app.assinantes.servico_atrasos"


def _rodada(nome, deduplicar):
    servico = ident(CODIGO, nome)
    terminal = ident(CODIGO, f"term-{nome}")

    argumentos = [
        "--id",
        servico,
        "--qos",
        QOS,
        "--sessao-efemera",
        "--reiniciar-banco",
        "--banco",
        str(config.RAIZ_DO_PROJETO / f"{CODIGO.lower()}-{nome}.db"),
        "--ate-mensagens",
        ENTREGAS_ESPERADAS,
        "--duracao",
        120,
        "--filtro",
        f"biblioteca/central/{terminal}/emprestimo",
        "--filtro",
        f"biblioteca/central/{terminal}/devolucao",
    ]
    if not deduplicar:
        argumentos.append("--sem-deduplicacao")

    assinante = iniciar_processo(MODULO_DO_SERVICO, *argumentos, identificador=servico)
    esperar_conexao(servico)

    publicador = iniciar_processo(
        MODULO_DO_PUBLICADOR,
        "--unidade",
        "central",
        "--terminal",
        terminal,
        "--qos",
        QOS,
        "--mensagens",
        MENSAGENS,
        "--intervalo",
        0.03,
        "--reenviar-a-cada",
        REENVIAR_A_CADA,
        "--semente",
        SEMENTE,
        identificador=terminal,
    )
    esperar_processo(publicador, 180)
    esperar_ate(lambda: len(recebidas(servico)) >= ENTREGAS_ESPERADAS, 60)
    encerrar_processo(assinante)

    resumo = resumo_de(servico)
    return {
        "servico": servico,
        "terminal": terminal,
        "publicadas": len(publicadas(terminal, aceitas_apenas=False)),
        "reenvios": len(eventos(terminal, "reenviado")),
        "recebidas": len(recebidas(servico)),
        "aplicadas": resumo.get("aplicadas", 0),
        "descartadas": resumo.get("descartadas", 0),
        "cobrancas": resumo.get("cobrancas_aplicadas", 0),
        "multa": resumo.get("multa_total_reais", 0.0),
        "persistidas": resumo.get("mensagens_persistidas", 0),
    }


def executar(coletor):
    sem = _rodada("sem-dedup", deduplicar=False)
    com = _rodada("com-dedup", deduplicar=True)

    coletor.registrar(
        CODIGO,
        "entregas produzidas por rodada (com reenvios)",
        ENTREGAS_ESPERADAS,
        com["publicadas"],
        f"{MENSAGENS} mensagens novas e {com['reenvios']} reenvios do mesmo envelope, "
        "simulando retentativa apos ack incerto.",
    )
    coletor.registrar(
        CODIGO,
        "QoS 2 nao evitou a chegada da repetida",
        ENTREGAS_ESPERADAS,
        com["recebidas"],
        "O reenvio e um PUBLISH novo para o broker: QoS 2 garante uma entrega por "
        "publicacao, nao um efeito por evento de negocio.",
    )
    coletor.registrar(
        CODIGO,
        "sem deduplicacao: efeitos aplicados",
        ENTREGAS_ESPERADAS,
        sem["aplicadas"],
        "Sem controle de identidade o consumidor aplica o efeito uma vez por entrega.",
    )
    coletor.registrar(
        CODIGO,
        "com deduplicacao: efeitos aplicados",
        MENSAGENS,
        com["aplicadas"],
        "A chave primaria em message_id transforma o reprocessamento em operacao inofensiva.",
    )
    coletor.registrar(
        CODIGO,
        "com deduplicacao: entregas descartadas",
        com["reenvios"],
        com["descartadas"],
        "Cada reenvio foi reconhecido como ja processado e descartado antes do efeito.",
    )
    coletor.registrar(
        CODIGO,
        "cobrancas de multa indevidas evitadas",
        True,
        f"{sem['cobrancas']} sem dedup contra {com['cobrancas']} com dedup",
        "Cobrar multa duas vezes e o efeito de negocio nao idempotente que o QoS nao protege.",
        sucesso=sem["cobrancas"] > com["cobrancas"],
    )
    coletor.registrar(
        CODIGO,
        "multa total cobrada",
        True,
        f"R$ {sem['multa']:.2f} sem dedup contra R$ {com['multa']:.2f} com dedup",
        "A diferenca em reais e a medida do prejuizo de confiar apenas no transporte.",
        sucesso=sem["multa"] > com["multa"],
    )
