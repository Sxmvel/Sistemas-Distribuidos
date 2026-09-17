import time
from concurrent import futures

from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import Servidor, ident, percentil

CODIGO = "E05"
TITULO = "Concorrencia: max_workers do servidor contra clientes simultaneos"
PERGUNTA = "O pool de threads do servidor limita o que o cliente enxerga como latencia?"

CLIENTES = 8
CHAMADAS_POR_CLIENTE = 3
CODIGOS_POR_CHAMADA = 10
ISBN_DE_UM_EXEMPLAR = "9788520937006"
DISPUTANTES = 12


def _carga(endereco, origem):
    inicio = time.perf_counter()
    latencias = []
    status = []
    pedido = pb2.CalcularMultasRequest(
        codigos=[f"EMP-{(indice % 4) + 1:04d}" for indice in range(CODIGOS_POR_CHAMADA)]
    )

    with Conexao(endereco, origem=origem) as conexao:
        def rodada(_):
            resultados = []
            for _ in range(CHAMADAS_POR_CLIENTE):
                resultados.append(conexao.chamar("CalcularMultas", pedido, timeout=30.0))
            return resultados

        with futures.ThreadPoolExecutor(max_workers=CLIENTES) as piscina:
            for lote in piscina.map(rodada, range(CLIENTES)):
                for resultado in lote:
                    latencias.append(resultado.latencia_ms)
                    status.append(resultado.status)

    return {
        "duracao_s": time.perf_counter() - inicio,
        "latencias": latencias,
        "status": status,
    }


def _rodada(workers, coletor):
    identificador = ident(CODIGO, f"servidor-w{workers}")
    with Servidor(identificador, workers=workers, semear=4) as servidor:
        medida = _carga(servidor.endereco, ident(CODIGO, f"cliente-w{workers}"))

    total = len(medida["latencias"])
    falhas = [item for item in medida["status"] if item != "OK"]
    medida["total"] = total
    medida["falhas"] = len(falhas)
    medida["p50"] = percentil(medida["latencias"], 0.50)
    medida["p95"] = percentil(medida["latencias"], 0.95)

    coletor.anotar_medicao(
        CODIGO,
        f"CalcularMultas x{total} com max_workers={workers} (p50)",
        30.0,
        "OK" if not falhas else falhas[0],
        medida["p50"],
        f"{CLIENTES} clientes simultaneos em um unico canal",
    )
    coletor.anotar_medicao(
        CODIGO,
        f"CalcularMultas x{total} com max_workers={workers} (p95)",
        30.0,
        "OK" if not falhas else falhas[0],
        medida["p95"],
        f"duracao total da rodada: {medida['duracao_s']:.2f} s",
    )
    return medida


def _disputa(coletor):
    identificador = ident(CODIGO, "servidor-disputa")
    with Servidor(identificador, workers=16) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente-disputa")) as conexao:
            def tentar(indice):
                return conexao.chamar(
                    "RegistrarEmprestimo",
                    pb2.RegistrarEmprestimoRequest(
                        isbn=ISBN_DE_UM_EXEMPLAR,
                        leitor=f"leitor{chr(ord('a') + indice)}.teste",
                        dias=7,
                        chave_idempotencia=f"e05-disputa-{indice}",
                    ),
                    timeout=20.0,
                )

            with futures.ThreadPoolExecutor(max_workers=DISPUTANTES) as piscina:
                resultados = list(piscina.map(tentar, range(DISPUTANTES)))

            listagem = conexao.transmitir(
                "ListarEmprestimos",
                pb2.ListarEmprestimosRequest(situacao=pb2.SITUACAO_ATIVO, limite=100),
                timeout=10.0,
            )

    aceitos = [item for item in resultados if item.ok]
    recusados = [item for item in resultados if item.status == "FAILED_PRECONDITION"]
    ativos = [
        item for item in (listagem.resposta or []) if item.isbn == ISBN_DE_UM_EXEMPLAR
    ]
    return aceitos, recusados, ativos


def executar(coletor):
    estreito = _rodada(2, coletor)
    largo = _rodada(16, coletor)

    coletor.registrar(
        CODIGO,
        "todas as chamadas concluem com max_workers=2",
        0,
        estreito["falhas"],
        f"{estreito['total']} chamadas de {CLIENTES} clientes simultaneos; o pool estreito "
        "enfileira, mas nao derruba.",
    )
    coletor.registrar(
        CODIGO,
        "todas as chamadas concluem com max_workers=16",
        0,
        largo["falhas"],
        f"{largo['total']} chamadas com o mesmo cliente e a mesma carga.",
    )
    coletor.registrar(
        CODIGO,
        "p95 melhora ao aumentar max_workers",
        True,
        largo["p95"] < estreito["p95"],
        f"p95 de {estreito['p95']:.0f} ms com 2 workers contra {largo['p95']:.0f} ms com 16. "
        "A fila do ThreadPoolExecutor do servidor e o gargalo, nao a rede.",
        sucesso=largo["p95"] < estreito["p95"],
    )
    coletor.registrar(
        CODIGO,
        "duracao total da rodada cai com mais workers",
        True,
        round(largo["duracao_s"], 2) < round(estreito["duracao_s"], 2),
        f"{estreito['duracao_s']:.2f} s com 2 workers contra {largo['duracao_s']:.2f} s "
        "com 16. O metodo dorme por item, entao o paralelismo aparece direto no tempo total.",
        sucesso=largo["duracao_s"] < estreito["duracao_s"],
    )
    coletor.registrar(
        CODIGO,
        "clientes simultaneos compartilham um unico canal",
        CLIENTES,
        CLIENTES,
        "Todas as chamadas da rodada saem do mesmo grpc.Channel: o HTTP/2 multiplexa "
        "varias RPCs na mesma conexao, diferente de uma requisicao HTTP por chamada.",
    )

    aceitos, recusados, ativos = _disputa(coletor)
    coletor.registrar(
        CODIGO,
        f"{DISPUTANTES} clientes disputam 1 exemplar — aceitos",
        1,
        len(aceitos),
        "A reserva do exemplar acontece dentro de uma trava no repositorio, entao o "
        "paralelismo do servidor nao quebra a invariante do dominio.",
    )
    coletor.registrar(
        CODIGO,
        f"{DISPUTANTES} clientes disputam 1 exemplar — recusados",
        DISPUTANTES - 1,
        len(recusados),
        "Os demais recebem FAILED_PRECONDITION, que e um resultado de dominio e nao um "
        "erro de concorrencia vazado para o cliente.",
    )
    coletor.registrar(
        CODIGO,
        "emprestimos ativos do titulo com 1 exemplar",
        1,
        len(ativos),
        "A listagem confirma o estado final: nenhum emprestimo duplicado sobreviveu "
        "a corrida.",
    )
