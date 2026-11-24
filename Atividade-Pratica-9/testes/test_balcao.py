import httpx
import pytest
from fastapi.testclient import TestClient

from observabilidade.contexto import cabecalho_causa, cabecalho_correlacao, cabecalho_mensagem, cabecalho_span_pai
from servicos.balcao import classificar_falha, criar_app
from servicos.configuracao import ConfiguracaoBalcao

replica_a = "http://acervo-a"
replica_b = "http://acervo-b"


class AcervoFalso:
    def __init__(self, comportamento):
        self.comportamento = comportamento
        self.chamadas = []

    async def __call__(self, requisicao):
        replica = f"{requisicao.url.scheme}://{requisicao.url.host}"
        self.chamadas.append((replica, dict(requisicao.headers)))
        acao = self.comportamento.get(replica, 200)
        if isinstance(acao, Exception):
            raise type(acao)(str(acao), request=requisicao)
        if acao == 200:
            return httpx.Response(200, json={"id": 1, "instancia": replica})
        return httpx.Response(acao, json={"status": acao})

    def replicas_chamadas(self):
        return [replica for replica, _ in self.chamadas]


@pytest.fixture
def montar(tmp_path):
    def montar(comportamento=None, quarentena_s=5.0):
        acervo = AcervoFalso(comportamento or {})
        configuracao = ConfiguracaoBalcao(
            instancia="balcao-t",
            replicas=(replica_a, replica_b),
            quarentena_s=quarentena_s,
            arquivo_de_log=str(tmp_path / "balcao.jsonl"),
        )
        return TestClient(criar_app(configuracao, transporte=httpx.MockTransport(acervo))), acervo, tmp_path / "balcao.jsonl"

    return montar


def test_repassa_a_resposta_do_acervo(montar):
    cliente, acervo, _ = montar()
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 200
    assert acervo.replicas_chamadas() == [replica_a]


def test_propaga_correlacao_e_encadeia_causa(montar, ler_log):
    cliente, acervo, log = montar()
    with cliente:
        cliente.get("/v1/livros/1", headers={cabecalho_correlacao: "c-1", cabecalho_mensagem: "m-cliente"})
    _, cabecalhos = acervo.chamadas[0]
    assert cabecalhos[cabecalho_correlacao.lower()] == "c-1"
    assert cabecalhos[cabecalho_causa.lower()] == "m-cliente"
    assert cabecalhos[cabecalho_mensagem.lower()] != "m-cliente"
    spans = {e["span_kind"]: e for e in ler_log(log) if e.get("span_kind")}
    assert spans["client"]["parent_span_id"] == spans["server"]["span_id"]
    assert cabecalhos[cabecalho_span_pai.lower()] == spans["client"]["span_id"]


def test_rodizio_alterna_as_replicas(montar):
    cliente, acervo, _ = montar()
    with cliente:
        for _ in range(4):
            cliente.get("/v1/livros/1")
    assert acervo.replicas_chamadas() == [replica_a, replica_b, replica_a, replica_b]


def test_failover_em_erro_500_com_a_mesma_mensagem(montar, ler_log):
    cliente, acervo, log = montar({replica_a: 500})
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 200
    assert acervo.replicas_chamadas() == [replica_a, replica_b]
    mensagens = {c[cabecalho_mensagem.lower()] for _, c in acervo.chamadas}
    assert len(mensagens) == 1
    tentativas = [e for e in ler_log(log) if e.get("span_kind") == "client"]
    assert [(t["attempt"], t["outcome"]) for t in tentativas] == [(1, "server_error"), (2, "success")]


def test_404_do_acervo_nao_dispara_failover(montar):
    cliente, acervo, _ = montar({replica_a: 404})
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 404
    assert acervo.replicas_chamadas() == [replica_a]


@pytest.mark.parametrize(
    ("falha", "status"),
    [
        (httpx.ConnectError("recusada"), 503),
        (httpx.RemoteProtocolError("caiu"), 503),
        (httpx.ReadTimeout("lento"), 504),
        (httpx.ConnectTimeout("sem syn"), 504),
    ],
)
def test_todas_as_replicas_falhando_viram_erro_de_aplicacao(montar, falha, status):
    cliente, acervo, _ = montar({replica_a: falha, replica_b: falha})
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == status
    assert resposta.headers["content-type"] == "application/problem+json"
    assert len(acervo.chamadas) == 2
    if status == 503:
        assert resposta.headers["Retry-After"] == "1"


def test_todas_com_500_viram_502(montar):
    cliente, _, _ = montar({replica_a: 500, replica_b: 500})
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 502
    assert resposta.json()["falhas"] == ["http_500", "http_500"]


def test_quarentena_tira_a_replica_do_rodizio(montar, ler_log):
    cliente, acervo, log = montar({replica_a: httpx.ConnectError("recusada")})
    with cliente:
        for _ in range(4):
            assert cliente.get("/v1/livros/1").status_code == 200
        saude = cliente.get("/v1/saude").json()
    assert acervo.replicas_chamadas().count(replica_a) == 1
    assert saude["replicas"][0]["em_quarentena"] is True
    [falha] = [e for e in ler_log(log) if e.get("outcome") == "transport_error"]
    assert falha["error"] == "conexao_recusada"
    assert falha["quarantine_s"] == 5.0


def test_quarentena_expira(montar):
    cliente, acervo, _ = montar({replica_a: httpx.ConnectError("recusada")}, quarentena_s=0.0)
    with cliente:
        for _ in range(4):
            cliente.get("/v1/livros/1")
    assert acervo.replicas_chamadas().count(replica_a) > 1


def test_vitrine_faz_uma_chamada_por_livro(montar, ler_log):
    cliente, acervo, log = montar()
    with cliente:
        resposta = cliente.get("/v1/vitrine", params={"quantidade": 4})
    assert resposta.status_code == 200
    assert len(resposta.json()["livros"]) == 4
    assert len(acervo.chamadas) == 4
    [servidor] = [e for e in ler_log(log) if e.get("span_kind") == "server"]
    assert servidor["dependency_calls"] == 4


def test_vitrine_falha_se_uma_chamada_falhar_em_todas_as_replicas(montar):
    cliente, _, _ = montar({replica_a: 500, replica_b: 500})
    with cliente:
        resposta = cliente.get("/v1/vitrine", params={"quantidade": 2})
    assert resposta.status_code == 502


@pytest.mark.parametrize(
    ("erro", "tipo"),
    [
        (httpx.ConnectTimeout("x"), "timeout_conexao"),
        (httpx.ReadTimeout("x"), "timeout_leitura"),
        (httpx.PoolTimeout("x"), "timeout_leitura"),
        (httpx.ConnectError("x"), "conexao_recusada"),
        (httpx.RemoteProtocolError("x"), "conexao_interrompida"),
        (httpx.ReadError("x"), "conexao_interrompida"),
        (httpx.UnsupportedProtocol("x"), "transporte"),
    ],
)
def test_classificacao_de_falhas_do_httpx(erro, tipo):
    assert classificar_falha(erro) == tipo
