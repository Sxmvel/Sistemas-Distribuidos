import pytest

from app.acervo import ISBN_INEXISTENTE
from contratos import emprestimos_pb2 as pb2

ISBN = "9788535910663"
ISBN_DE_UM_EXEMPLAR = "9788520937006"


def pedido(**campos):
    base = {"isbn": ISBN, "leitor": "ana.souza", "dias": 7}
    base.update(campos)
    return pb2.RegistrarEmprestimoRequest(**base)


ENTRADAS_INVALIDAS = [
    ("isbn vazio", pedido(isbn=""), "isbn"),
    ("isbn curto", pedido(isbn="123"), "isbn"),
    ("isbn com letras", pedido(isbn="978853591066X"), "isbn"),
    ("leitor vazio", pedido(leitor=""), "leitor"),
    ("leitor com espaco", pedido(leitor="Ana Souza"), "leitor"),
    ("dias negativo", pedido(dias=-1), "dias"),
    ("dias acima do maximo", pedido(dias=99), "dias"),
    ("unidade desconhecida", pedido(unidade="filial"), "unidade"),
]


@pytest.mark.parametrize("rotulo, entrada, campo", ENTRADAS_INVALIDAS)
def test_entrada_invalida_devolve_invalid_argument(conexao, rotulo, entrada, campo):
    resultado = conexao.chamar("RegistrarEmprestimo", entrada, timeout=5.0)
    assert resultado.status == "INVALID_ARGUMENT"
    assert resultado.campo == campo
    assert campo in resultado.detalhe


def test_isbn_fora_do_acervo_devolve_not_found(conexao):
    resultado = conexao.chamar(
        "RegistrarEmprestimo", pedido(isbn=ISBN_INEXISTENTE), timeout=5.0
    )
    assert resultado.status == "NOT_FOUND"


def test_consulta_de_codigo_inexistente_devolve_not_found(conexao):
    resultado = conexao.chamar(
        "ConsultarEmprestimo",
        pb2.ConsultarEmprestimoRequest(codigo="EMP-9999"),
        timeout=5.0,
    )
    assert resultado.status == "NOT_FOUND"


def test_consulta_sem_codigo_devolve_invalid_argument(conexao):
    resultado = conexao.chamar(
        "ConsultarEmprestimo", pb2.ConsultarEmprestimoRequest(codigo=""), timeout=5.0
    )
    assert resultado.status == "INVALID_ARGUMENT"


def test_sem_exemplar_devolve_failed_precondition(conexao):
    conexao.chamar(
        "RegistrarEmprestimo",
        pedido(isbn=ISBN_DE_UM_EXEMPLAR, chave_idempotencia="a"),
        timeout=5.0,
    )
    resultado = conexao.chamar(
        "RegistrarEmprestimo",
        pedido(isbn=ISBN_DE_UM_EXEMPLAR, leitor="bruno.lima", chave_idempotencia="b"),
        timeout=5.0,
    )
    assert resultado.status == "FAILED_PRECONDITION"


def test_segunda_devolucao_devolve_failed_precondition(conexao):
    criado = conexao.chamar("RegistrarEmprestimo", pedido(), timeout=5.0)
    codigo = criado.resposta.emprestimo.codigo
    primeira = conexao.chamar(
        "RegistrarDevolucao", pb2.RegistrarDevolucaoRequest(codigo=codigo), timeout=5.0
    )
    segunda = conexao.chamar(
        "RegistrarDevolucao", pb2.RegistrarDevolucaoRequest(codigo=codigo), timeout=5.0
    )
    assert primeira.ok
    assert segunda.status == "FAILED_PRECONDITION"


def test_data_de_devolucao_malformada_devolve_invalid_argument(conexao):
    criado = conexao.chamar("RegistrarEmprestimo", pedido(), timeout=5.0)
    resultado = conexao.chamar(
        "RegistrarDevolucao",
        pb2.RegistrarDevolucaoRequest(
            codigo=criado.resposta.emprestimo.codigo, devolvido_em="16/09/2026"
        ),
        timeout=5.0,
    )
    assert resultado.status == "INVALID_ARGUMENT"
    assert resultado.campo == "devolvido_em"


def test_chave_reusada_com_outro_pedido_devolve_already_exists(conexao):
    conexao.chamar(
        "RegistrarEmprestimo", pedido(chave_idempotencia="repetida"), timeout=5.0
    )
    resultado = conexao.chamar(
        "RegistrarEmprestimo",
        pedido(leitor="bruno.lima", chave_idempotencia="repetida"),
        timeout=5.0,
    )
    assert resultado.status == "ALREADY_EXISTS"


def test_lista_de_codigos_vazia_devolve_invalid_argument(conexao):
    resultado = conexao.chamar(
        "CalcularMultas", pb2.CalcularMultasRequest(codigos=[]), timeout=5.0
    )
    assert resultado.status == "INVALID_ARGUMENT"


def test_lista_de_codigos_acima_do_limite_devolve_invalid_argument(conexao):
    resultado = conexao.chamar(
        "CalcularMultas",
        pb2.CalcularMultasRequest(codigos=["EMP-0001"] * 501),
        timeout=5.0,
    )
    assert resultado.status == "INVALID_ARGUMENT"


def test_codigo_desconhecido_no_calculo_devolve_not_found(conexao):
    resultado = conexao.chamar(
        "CalcularMultas",
        pb2.CalcularMultasRequest(codigos=["EMP-9999"]),
        timeout=5.0,
    )
    assert resultado.status == "NOT_FOUND"


def test_status_de_erro_carrega_id_de_correlacao(conexao):
    resultado = conexao.chamar("RegistrarEmprestimo", pedido(isbn=""), timeout=5.0)
    assert resultado.metadados.get("x-correlacao-id")


def test_politica_de_retry_muda_com_o_status(conexao):
    invalido = conexao.chamar("RegistrarEmprestimo", pedido(isbn=""), timeout=5.0)
    assert invalido.politica == "corrigir a chamada, nunca repetir"
