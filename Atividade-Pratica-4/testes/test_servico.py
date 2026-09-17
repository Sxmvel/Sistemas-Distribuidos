from datetime import date, timedelta

from app import config
from contratos import emprestimos_pb2 as pb2

ISBN = "9788535910663"
ISBN_DE_UM_EXEMPLAR = "9788520937006"


def pedido(**campos):
    base = {"isbn": ISBN, "leitor": "ana.souza", "dias": 7}
    base.update(campos)
    return pb2.RegistrarEmprestimoRequest(**base)


def registrar(conexao, **campos):
    return conexao.chamar("RegistrarEmprestimo", pedido(**campos), timeout=5.0)


def test_emprestimo_valido_devolve_codigo_e_prazo(conexao):
    resultado = registrar(conexao)
    assert resultado.ok
    emprestimo = resultado.resposta.emprestimo
    assert emprestimo.codigo.startswith("EMP-")
    assert emprestimo.titulo == "Dom Casmurro"
    assert emprestimo.previsto_para == (date.today() + timedelta(days=7)).isoformat()
    assert emprestimo.situacao == pb2.SITUACAO_ATIVO


def test_dias_ausente_usa_o_prazo_padrao(conexao):
    resultado = registrar(conexao, dias=0)
    assert resultado.ok
    esperado = date.today() + timedelta(days=config.PRAZO_EM_DIAS)
    assert resultado.resposta.emprestimo.previsto_para == esperado.isoformat()


def test_unidade_ausente_usa_a_unidade_padrao(conexao):
    resultado = registrar(conexao)
    assert resultado.resposta.emprestimo.unidade == "central"


def test_exemplares_disponiveis_diminuem_a_cada_emprestimo(conexao):
    primeiro = registrar(conexao, chave_idempotencia="a")
    segundo = registrar(conexao, leitor="bruno.lima", chave_idempotencia="b")
    assert primeiro.resposta.exemplares_disponiveis == 2
    assert segundo.resposta.exemplares_disponiveis == 1


def test_chave_de_idempotencia_reaproveita_o_mesmo_emprestimo(conexao):
    primeiro = registrar(conexao, chave_idempotencia="mesma")
    segundo = registrar(conexao, chave_idempotencia="mesma")
    assert segundo.ok
    assert segundo.resposta.reaproveitado is True
    assert segundo.resposta.emprestimo.codigo == primeiro.resposta.emprestimo.codigo


def test_sem_chave_cada_chamada_cria_um_emprestimo(conexao):
    primeiro = registrar(conexao)
    segundo = registrar(conexao)
    assert primeiro.resposta.emprestimo.codigo != segundo.resposta.emprestimo.codigo


def test_consulta_devolve_o_emprestimo_criado(conexao):
    criado = registrar(conexao).resposta.emprestimo
    consulta = conexao.chamar(
        "ConsultarEmprestimo",
        pb2.ConsultarEmprestimoRequest(codigo=criado.codigo),
        timeout=5.0,
    )
    assert consulta.resposta.emprestimo == criado


def test_consulta_aceita_codigo_em_minusculas(conexao):
    criado = registrar(conexao).resposta.emprestimo
    consulta = conexao.chamar(
        "ConsultarEmprestimo",
        pb2.ConsultarEmprestimoRequest(codigo=criado.codigo.lower()),
        timeout=5.0,
    )
    assert consulta.ok


def test_devolucao_no_prazo_nao_gera_multa(conexao):
    criado = registrar(conexao).resposta.emprestimo
    devolucao = conexao.chamar(
        "RegistrarDevolucao",
        pb2.RegistrarDevolucaoRequest(codigo=criado.codigo),
        timeout=5.0,
    )
    assert devolucao.ok
    assert devolucao.resposta.dias_de_atraso == 0
    assert devolucao.resposta.multa == 0.0
    assert devolucao.resposta.emprestimo.situacao == pb2.SITUACAO_DEVOLVIDO


def test_devolucao_atrasada_cobra_por_dia(conexao):
    criado = registrar(conexao).resposta.emprestimo
    atrasada = (date.today() + timedelta(days=10)).isoformat()
    devolucao = conexao.chamar(
        "RegistrarDevolucao",
        pb2.RegistrarDevolucaoRequest(codigo=criado.codigo, devolvido_em=atrasada),
        timeout=5.0,
    )
    assert devolucao.resposta.dias_de_atraso == 3
    assert devolucao.resposta.multa == round(3 * config.VALOR_DA_MULTA_POR_DIA, 2)


def test_devolucao_libera_o_exemplar(conexao):
    criado = registrar(conexao, isbn=ISBN_DE_UM_EXEMPLAR, chave_idempotencia="x")
    bloqueado = registrar(
        conexao, isbn=ISBN_DE_UM_EXEMPLAR, leitor="bruno.lima", chave_idempotencia="y"
    )
    assert bloqueado.status == "FAILED_PRECONDITION"

    conexao.chamar(
        "RegistrarDevolucao",
        pb2.RegistrarDevolucaoRequest(codigo=criado.resposta.emprestimo.codigo),
        timeout=5.0,
    )
    liberado = registrar(
        conexao, isbn=ISBN_DE_UM_EXEMPLAR, leitor="bruno.lima", chave_idempotencia="z"
    )
    assert liberado.ok


def test_calculo_de_multas_soma_os_codigos(conexao):
    codigos = []
    for indice, leitor in enumerate(("ana.souza", "bruno.lima")):
        criado = registrar(conexao, leitor=leitor, chave_idempotencia=f"m{indice}")
        codigos.append(criado.resposta.emprestimo.codigo)

    referencia = (date.today() + timedelta(days=9)).isoformat()
    resultado = conexao.chamar(
        "CalcularMultas",
        pb2.CalcularMultasRequest(codigos=codigos, referencia=referencia),
        timeout=10.0,
    )
    assert resultado.ok
    assert resultado.resposta.quantidade == 2
    assert all(item.dias_de_atraso == 2 for item in resultado.resposta.itens)
    assert resultado.resposta.total == round(4 * config.VALOR_DA_MULTA_POR_DIA, 2)
