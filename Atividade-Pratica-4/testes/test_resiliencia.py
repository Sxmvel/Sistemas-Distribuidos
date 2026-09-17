import socket
from concurrent import futures

from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2

ISBN = "9788535910663"
ISBN_DE_UM_EXEMPLAR = "9788520937006"


def pedido(**campos):
    base = {"isbn": ISBN, "leitor": "ana.souza", "dias": 7}
    base.update(campos)
    return pb2.RegistrarEmprestimoRequest(**base)


def porta_livre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tomada:
        tomada.bind(("127.0.0.1", 0))
        return tomada.getsockname()[1]


def semear(conexao, quantidade):
    codigos = []
    for indice in range(quantidade):
        criado = conexao.chamar(
            "RegistrarEmprestimo",
            pedido(chave_idempotencia=f"semente-{indice}"),
            timeout=5.0,
        )
        codigos.append(criado.resposta.emprestimo.codigo)
    return codigos


def test_deadline_curto_devolve_deadline_exceeded(conexao):
    codigos = semear(conexao, 1) * 60
    resultado = conexao.chamar(
        "CalcularMultas", pb2.CalcularMultasRequest(codigos=codigos), timeout=0.1
    )
    assert resultado.status == "DEADLINE_EXCEEDED"


def test_deadline_folgado_conclui_a_mesma_chamada(conexao):
    codigos = semear(conexao, 1) * 60
    resultado = conexao.chamar(
        "CalcularMultas", pb2.CalcularMultasRequest(codigos=codigos), timeout=10.0
    )
    assert resultado.ok
    assert resultado.resposta.quantidade == 60


def test_latencia_do_deadline_nao_espera_o_fim_do_trabalho(conexao):
    codigos = semear(conexao, 1) * 200
    resultado = conexao.chamar(
        "CalcularMultas", pb2.CalcularMultasRequest(codigos=codigos), timeout=0.2
    )
    assert resultado.status == "DEADLINE_EXCEEDED"
    assert resultado.latencia_ms < 1000


def test_servidor_desligado_devolve_unavailable():
    with Conexao(f"127.0.0.1:{porta_livre()}", origem="teste-orfao") as conexao:
        resultado = conexao.chamar("RegistrarEmprestimo", pedido(), timeout=6.0)
    assert resultado.status == "UNAVAILABLE"


def test_deadline_curto_com_servidor_desligado_mascara_a_causa():
    with Conexao(f"127.0.0.1:{porta_livre()}", origem="teste-orfao-curto") as conexao:
        resultado = conexao.chamar("RegistrarEmprestimo", pedido(), timeout=0.3)
    assert resultado.status == "DEADLINE_EXCEEDED"


def test_streaming_entrega_todos_os_ativos(conexao):
    semear(conexao, 3)
    resultado = conexao.transmitir(
        "ListarEmprestimos",
        pb2.ListarEmprestimosRequest(situacao=pb2.SITUACAO_ATIVO, limite=50),
        timeout=5.0,
    )
    assert resultado.ok
    assert len(resultado.resposta) == 3


def test_streaming_respeita_o_limite(conexao):
    semear(conexao, 3)
    resultado = conexao.transmitir(
        "ListarEmprestimos",
        pb2.ListarEmprestimosRequest(limite=2),
        timeout=5.0,
    )
    assert len(resultado.resposta) == 2


def test_streaming_filtra_por_leitor(conexao):
    semear(conexao, 2)
    conexao.chamar(
        "RegistrarEmprestimo",
        pedido(leitor="bruno.lima", chave_idempotencia="outro"),
        timeout=5.0,
    )
    resultado = conexao.transmitir(
        "ListarEmprestimos",
        pb2.ListarEmprestimosRequest(leitor="bruno.lima"),
        timeout=5.0,
    )
    assert len(resultado.resposta) == 1
    assert resultado.resposta[0].leitor == "bruno.lima"


def test_disputa_pelo_unico_exemplar_aceita_apenas_um(conexao):
    def tentar(indice):
        return conexao.chamar(
            "RegistrarEmprestimo",
            pedido(
                isbn=ISBN_DE_UM_EXEMPLAR,
                leitor=f"leitor{chr(ord('a') + indice)}.teste",
                chave_idempotencia=f"disputa-{indice}",
            ),
            timeout=10.0,
        )

    with futures.ThreadPoolExecutor(max_workers=10) as piscina:
        resultados = list(piscina.map(tentar, range(10)))

    aceitos = [item for item in resultados if item.ok]
    recusados = [item for item in resultados if item.status == "FAILED_PRECONDITION"]
    assert len(aceitos) == 1
    assert len(recusados) == 9


def test_chamadas_concorrentes_compartilham_o_mesmo_canal(conexao):
    semear(conexao, 1)

    def consultar(_):
        return conexao.chamar(
            "ConsultarEmprestimo",
            pb2.ConsultarEmprestimoRequest(codigo="EMP-0001"),
            timeout=10.0,
        )

    with futures.ThreadPoolExecutor(max_workers=12) as piscina:
        resultados = list(piscina.map(consultar, range(24)))

    assert all(item.ok for item in resultados)


def test_metricas_do_cliente_agregam_por_metodo(conexao):
    semear(conexao, 2)
    conexao.chamar("RegistrarEmprestimo", pedido(isbn=""), timeout=5.0)
    por_metodo, por_status = conexao.metricas.resumo()
    assert por_metodo["RegistrarEmprestimo"]["chamadas"] == 3
    assert por_status["INVALID_ARGUMENT"] == 1
    assert por_status["OK"] == 2
