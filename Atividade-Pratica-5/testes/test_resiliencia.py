import pytest

from cliente import resiliencia
from cliente.resiliencia import Disjuntor, Tentativa, calcular_espera, chamar_com_retry


class RespostaFalsa:
    def __init__(self, status):
        self.status_code = status
        self.ok = status < 400


def roteiro(*categorias):
    sequencia = iter(categorias)

    def executar(metodo, url, numero, timeout, correlacao, cabecalhos=None, **kwargs):
        categoria = next(sequencia)
        if isinstance(categoria, int):
            resposta = RespostaFalsa(categoria)
            return Tentativa(numero, url, 1.0, categoria, resiliencia.classificar_status(categoria)), resposta, None
        return Tentativa(numero, url, 1.0, None, categoria), None, OSError(categoria)

    return executar


def sem_espera(_):
    return None


def test_espera_cresce_exponencialmente_dentro_da_faixa_do_jitter():
    esperas = [calcular_espera(indice, base=0.2, jitter=0.1) for indice in range(4)]

    for indice, espera in enumerate(esperas):
        assert 0.2 * 2**indice <= espera <= 0.2 * 2**indice + 0.1


def test_espera_respeita_o_teto():
    assert calcular_espera(10, base=0.2, jitter=0.0, teto=5.0) == 5.0


def test_para_na_primeira_resposta_de_sucesso(monkeypatch):
    monkeypatch.setattr(resiliencia, "executar_tentativa", roteiro(503, 503, 200, 200))

    resultado = chamar_com_retry("GET", "http://x", dormir=sem_espera)

    assert resultado.ok
    assert [item.status for item in resultado.tentativas] == [503, 503, 200]


def test_nao_repete_erro_do_cliente(monkeypatch):
    monkeypatch.setattr(resiliencia, "executar_tentativa", roteiro(422, 200))

    resultado = chamar_com_retry("GET", "http://x", dormir=sem_espera)

    assert len(resultado.tentativas) == 1
    assert resultado.categoria == "erro-do-cliente"


def test_limite_de_tentativas_e_respeitado(monkeypatch):
    monkeypatch.setattr(resiliencia, "executar_tentativa", roteiro(*["timeout-de-leitura"] * 10))
    esperas = []

    resultado = chamar_com_retry("GET", "http://x", tentativas=4, dormir=esperas.append, sortear=lambda a, b: 0)

    assert len(resultado.tentativas) == 4
    assert esperas == [0.2, 0.4, 0.8]
    assert resultado.tentativas[-1].espera_s == 0.0


@pytest.mark.parametrize(
    "categoria", ["timeout-de-leitura", "timeout-de-conexao", "conexao-recusada", "conexao-interrompida"]
)
def test_falhas_de_transporte_sao_transitorias(categoria):
    assert Tentativa(1, "x", 1.0, None, categoria).transitoria


def test_disjuntor_abre_rejeita_e_fecha_apos_teste_bem_sucedido(monkeypatch):
    agora = [0.0]
    disjuntor = Disjuntor(limite_de_falhas=3, tempo_aberto=1.0, relogio=lambda: agora[0])
    monkeypatch.setattr(
        resiliencia, "executar_tentativa", roteiro("conexao-recusada", "conexao-recusada", "conexao-recusada", 200)
    )

    for _ in range(3):
        disjuntor.chamar("GET", "http://x")
    rejeitada = disjuntor.chamar("GET", "http://x")
    agora[0] = 1.5
    teste = disjuntor.chamar("GET", "http://x")

    assert rejeitada.categoria == "circuito-aberto"
    assert teste.ok
    assert disjuntor.historico == [("fechado", "aberto"), ("aberto", "meio-aberto"), ("meio-aberto", "fechado")]


def test_disjuntor_reabre_se_o_teste_falhar(monkeypatch):
    agora = [0.0]
    disjuntor = Disjuntor(limite_de_falhas=1, tempo_aberto=1.0, relogio=lambda: agora[0])
    monkeypatch.setattr(resiliencia, "executar_tentativa", roteiro("conexao-recusada", "conexao-recusada"))

    disjuntor.chamar("GET", "http://x")
    agora[0] = 1.2
    disjuntor.chamar("GET", "http://x")

    assert disjuntor.estado == "aberto"
    assert disjuntor.aberto_desde == 1.2
