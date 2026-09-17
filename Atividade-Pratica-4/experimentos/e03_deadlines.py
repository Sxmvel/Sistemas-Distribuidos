from app import config
from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import (
    Servidor,
    chamadas_concluidas,
    esperar_ate,
    eventos,
    ident,
)

CODIGO = "E03"
TITULO = "Deadlines de 100 ms, 1 s e 3 s no mesmo metodo"
PERGUNTA = "Quanto tempo o cliente aceita esperar e o que o servidor faz quando ele desiste?"

CODIGOS_POR_CHAMADA = 40
DEADLINES = (0.1, 1.0, 3.0)
CUSTO = config.CUSTO_POR_CODIGO_NA_MULTA
LIMITE_FINITO = 1_000_000


def executar(coletor):
    identificador = ident(CODIGO, "servidor")
    custo_total = CODIGOS_POR_CHAMADA * CUSTO

    with Servidor(identificador, semear=4) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente")) as conexao:
            codigos = [f"EMP-{indice:04d}" for indice in range(1, 5)] * 10
            pedido = pb2.CalcularMultasRequest(codigos=codigos)

            resultados = {}
            for deadline in DEADLINES:
                resultado = coletor.medir(
                    CODIGO,
                    f"CalcularMultas ({CODIGOS_POR_CHAMADA} codigos)",
                    deadline,
                    conexao.chamar("CalcularMultas", pedido, timeout=deadline),
                    f"custo no servidor ~{custo_total:.2f} s",
                )
                resultados[deadline] = resultado

            sem_limite = coletor.medir(
                CODIGO,
                f"CalcularMultas ({CODIGOS_POR_CHAMADA} codigos)",
                None,
                conexao.chamar("CalcularMultas", pedido, timeout=None),
                "chamada sem deadline, para contraste",
            )

    coletor.registrar(
        CODIGO,
        "deadline de 0,1 s contra trabalho de ~1,2 s",
        "DEADLINE_EXCEEDED",
        resultados[0.1].status,
        "O cliente desiste antes do servidor terminar. O status nao diz se houve efeito "
        "no servidor — so diz que o tempo acabou.",
    )
    coletor.registrar(
        CODIGO,
        "deadline de 1 s contra trabalho de ~1,2 s",
        "DEADLINE_EXCEEDED",
        resultados[1.0].status,
        "Um deadline plausivel ainda estoura quando o custo real supera a estimativa: "
        "o limite precisa vir do SLA, nao do otimismo.",
    )
    coletor.registrar(
        CODIGO,
        "deadline de 3 s contra trabalho de ~1,2 s",
        "OK",
        resultados[3.0].status,
        "Com folga suficiente a mesma chamada, o mesmo pedido e o mesmo servidor "
        "respondem normalmente. O que mudou foi so o orcamento de tempo.",
    )
    coletor.registrar(
        CODIGO,
        "chamada sem deadline conclui",
        "OK",
        sem_limite.status,
        "Sem limite a chamada termina, mas o cliente fica preso ao tempo do servidor: "
        "e exatamente o recurso bloqueado por tempo indeterminado da secao 6.5.",
    )

    for deadline in (0.1, 1.0):
        latencia = next(
            item.latencia_ms
            for item in coletor.medicoes_do_cenario(CODIGO)
            if item.deadline == f"{deadline:g} s"
        )
        coletor.registrar(
            CODIGO,
            f"latencia observada com deadline de {deadline:g} s",
            f"<= {deadline * 1000 + 150:.0f} ms",
            latencia,
            "O cliente retorna proximo ao deadline, nao ao fim do trabalho: o custo de "
            "uma chamada lenta vira previsivel para quem chama.",
            sucesso=latencia <= deadline * 1000 + 150,
        )

    esperar_ate(
        lambda: len(chamadas_concluidas(identificador, "CalcularMultas")) >= 4, limite=15
    )
    concluidas = chamadas_concluidas(identificador, "CalcularMultas")
    abandonadas = [
        item for item in concluidas if item["status"] == "ABANDONADA_PELO_CLIENTE"
    ]

    coletor.registrar(
        CODIGO,
        "chamadas que o servidor abandonou por cancelamento",
        2,
        len(abandonadas),
        "As duas chamadas que estouraram o deadline foram interrompidas no servidor. "
        "O servidor checa context.is_active() a cada item e para de trabalhar.",
    )

    if abandonadas:
        curta = min(abandonadas, key=lambda item: item["processados"])
        coletor.registrar(
            CODIGO,
            "itens processados antes de abandonar o deadline de 0,1 s",
            f"< {CODIGOS_POR_CHAMADA}",
            curta["processados"],
            f"O servidor parou em {curta['processados']} de {curta['total']} itens. "
            "Trabalho que nao interessa mais ao cliente nao consome CPU ate o fim.",
            sucesso=curta["processados"] < CODIGOS_POR_CHAMADA,
        )

    recebidas = [
        item
        for item in eventos(identificador, "chamada-recebida")
        if item.get("metodo") == "CalcularMultas"
    ]
    prazos = [item.get("prazo_restante_s") for item in recebidas]
    finitos = sorted(valor for valor in prazos if valor is not None and valor < LIMITE_FINITO)
    coletor.registrar(
        CODIGO,
        "servidor enxerga o prazo restante das chamadas com deadline",
        len(DEADLINES),
        len(finitos),
        "O deadline viaja no cabecalho da RPC. Os prazos vistos pelo servidor foram "
        f"{', '.join(f'{valor:.2f} s' for valor in finitos)} — cada um um pouco menor que o "
        "deadline do cliente, porque o tempo de rede ja foi descontado. E isso que permite "
        "propagar o orcamento de tempo para o proximo hop em vez de reiniciar o timeout.",
    )
    infinitos = [
        valor for valor in prazos if valor is not None and valor >= LIMITE_FINITO
    ]
    coletor.registrar(
        CODIGO,
        "chamada sem deadline chega ao servidor com prazo praticamente infinito",
        1,
        len(infinitos),
        f"time_remaining() devolveu {infinitos[0]:.3g} s (cerca de "
        f"{infinitos[0] / 31_536_000:.0e} anos) em vez de None. Na pratica o servidor nao "
        "tem limite e nunca cancela sozinho: o resultado pode nao interessar mais a "
        "ninguem e o trabalho continua."
        if infinitos
        else "Nenhuma chamada sem deadline foi registrada.",
    )
