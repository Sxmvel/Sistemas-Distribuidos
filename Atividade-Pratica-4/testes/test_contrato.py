import pytest

from app import config
from contratos import emprestimos_pb2 as pb2

SERVICO = pb2.DESCRIPTOR.services_by_name["Emprestimos"]

METODOS = {
    "RegistrarEmprestimo": (False, False),
    "ConsultarEmprestimo": (False, False),
    "RegistrarDevolucao": (False, False),
    "CalcularMultas": (False, False),
    "ListarEmprestimos": (False, True),
}


def test_pacote_versionado_no_contrato():
    assert pb2.DESCRIPTOR.package == "biblioteca.emprestimos.v1"


def test_contrato_tem_pelo_menos_tres_metodos():
    assert len(SERVICO.methods) >= 3


@pytest.mark.parametrize("nome, fluxos", METODOS.items())
def test_assinatura_de_cada_metodo(nome, fluxos):
    metodo = SERVICO.methods_by_name[nome]
    assert (metodo.client_streaming, metodo.server_streaming) == fluxos


def test_contrato_tem_pelo_menos_tres_mensagens_proprias():
    assert len(pb2.DESCRIPTOR.message_types_by_name) >= 3


def test_numero_de_campo_removido_fica_reservado():
    texto = (config.RAIZ_DO_PROJETO / "contratos" / "emprestimos.proto").read_text(
        encoding="utf-8"
    )
    assert "reserved 15;" in texto
    assert 'reserved "telefone_do_leitor";' in texto
    numeros = {campo.number for campo in pb2.Emprestimo.DESCRIPTOR.fields}
    assert 15 not in numeros


def test_campo_novo_da_v2_existe_nos_dois_lados():
    assert "unidade" in {campo.name for campo in pb2.Emprestimo.DESCRIPTOR.fields}
    assert "unidade" in {
        campo.name for campo in pb2.RegistrarEmprestimoRequest.DESCRIPTOR.fields
    }


def test_campo_novo_tem_numero_no_fim_da_mensagem():
    unidade = pb2.Emprestimo.DESCRIPTOR.fields_by_name["unidade"]
    outros = [
        campo.number
        for campo in pb2.Emprestimo.DESCRIPTOR.fields
        if campo.name != "unidade"
    ]
    assert unidade.number > max(outros)


def test_round_trip_preserva_a_mensagem():
    original = pb2.Emprestimo(
        codigo="EMP-0001",
        isbn="9788535910663",
        titulo="Dom Casmurro",
        leitor="ana.souza",
        emprestado_em="2026-09-16",
        previsto_para="2026-09-23",
        situacao=pb2.SITUACAO_ATIVO,
        unidade="anexo",
    )
    copia = pb2.Emprestimo()
    copia.ParseFromString(original.SerializeToString())
    assert copia == original


def test_campo_ausente_volta_com_valor_padrao():
    vazio = pb2.RegistrarEmprestimoRequest(isbn="9788535910663", leitor="ana.souza")
    assert vazio.dias == 0
    assert vazio.unidade == ""
    assert vazio.chave_idempotencia == ""


def test_enum_tem_zero_reservado_para_nao_informado():
    assert pb2.Situacao.Name(0) == "SITUACAO_NAO_INFORMADA"
    assert pb2.Emprestimo().situacao == pb2.SITUACAO_NAO_INFORMADA


def test_mensagem_sem_o_campo_novo_e_prefixo_da_mensagem_com_o_campo():
    sem = pb2.Emprestimo(codigo="EMP-0001", leitor="ana.souza")
    com = pb2.Emprestimo(codigo="EMP-0001", leitor="ana.souza", unidade="anexo")
    assert com.SerializeToString().startswith(sem.SerializeToString())
