import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from medicao.carga import classificar_excecao, executar_carga


class Atendente(BaseHTTPRequestHandler):
    status = 200
    vistos = []

    def do_GET(self):
        Atendente.vistos.append(dict(self.headers))
        self.send_response(Atendente.status)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *_):
        pass


@pytest.fixture
def servidor():
    Atendente.status = 200
    Atendente.vistos = []
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Atendente)
    linha = threading.Thread(target=servidor.serve_forever, daemon=True)
    linha.start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/"
    servidor.shutdown()
    servidor.server_close()


@pytest.mark.parametrize(
    ("erro", "esperado"),
    [
        (requests.exceptions.ConnectTimeout("x"), "timeout_conexao"),
        (requests.exceptions.ReadTimeout("x"), "timeout_leitura"),
        (requests.exceptions.ConnectionError("[WinError 10061] a máquina de destino as recusou ativamente"), "conexao_recusada"),
        (requests.exceptions.ConnectionError("Connection refused"), "conexao_recusada"),
        (requests.exceptions.ConnectionError("Connection aborted. RemoteDisconnected"), "conexao_interrompida"),
        (requests.exceptions.ConnectionError("[WinError 10054] reset"), "conexao_interrompida"),
        (requests.exceptions.ConnectionError("outra coisa"), "conexao"),
        (requests.exceptions.InvalidURL("x"), "transporte"),
    ],
)
def test_classificacao_de_erro_de_transporte(erro, esperado):
    assert classificar_excecao(erro) == esperado


def test_carga_separa_aquecimento_e_respeita_o_total(servidor):
    resultado = executar_carga(servidor, concorrencia=3, total=30, aquecimento=5)
    assert len(resultado.amostras) == 35
    assert len(resultado.aquecimento) == 5
    assert len(resultado.medidas) == 30
    assert all(a.classe == "sucesso" for a in resultado.amostras)


def test_cada_requisicao_leva_identificadores_proprios(servidor):
    resultado = executar_carga(servidor, total=10)
    ids = {a.correlation_id for a in resultado.amostras}
    assert len(ids) == 10
    assert {v["X-Correlation-ID"] for v in Atendente.vistos} == ids
    assert len({v["X-Message-ID"] for v in Atendente.vistos}) == 10


def test_status_de_erro_vira_erro_de_aplicacao(servidor):
    Atendente.status = 503
    resultado = executar_carga(servidor, total=5)
    assert {(a.classe, a.detalhe) for a in resultado.amostras} == {("erro_aplicacao", "http_503")}


def test_criterio_de_aborto_interrompe_a_carga(servidor):
    Atendente.status = 500
    resultado = executar_carga(servidor, concorrencia=2, duracao_s=10, limite_de_erro=0.5, minimo_para_abortar=5)
    assert resultado.abortado
    assert resultado.duracao_s < 5
    assert "taxa de erro" in resultado.motivo_do_aborto


def test_eventos_agendados_executam_no_instante(servidor):
    executados = []
    resultado = executar_carga(servidor, duracao_s=0.6, eventos=[(0.3, "marco", lambda: executados.append(True))])
    assert executados == [True]
    assert resultado.marcos[0]["rotulo"] == "marco"
    assert 0.25 <= resultado.marcos[0]["inicio_s"] <= 0.5


def test_exige_total_ou_duracao(servidor):
    with pytest.raises(ValueError):
        executar_carga(servidor)
