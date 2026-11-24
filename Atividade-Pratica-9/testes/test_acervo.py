import pytest
from fastapi.testclient import TestClient

from observabilidade.contexto import cabecalho_causa, cabecalho_correlacao, cabecalho_mensagem, cabecalho_span_pai
from servicos.acervo import criar_app
from servicos.configuracao import ConfiguracaoAcervo


@pytest.fixture
def montar(tmp_path):
    def montar(**opcoes):
        configuracao = ConfiguracaoAcervo(instancia="acervo-t", tempo_servico_ms=0, arquivo_de_log=str(tmp_path / "acervo.jsonl"), **opcoes)
        return TestClient(criar_app(configuracao)), tmp_path / "acervo.jsonl"

    return montar


def test_consulta_livro_existente(montar):
    cliente, _ = montar()
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 200
    assert resposta.json()["titulo"] == "Dom Casmurro"
    assert resposta.json()["instancia"] == "acervo-t"


def test_livro_inexistente_responde_problema_404(montar):
    cliente, _ = montar()
    with cliente:
        resposta = cliente.get("/v1/livros/999")
    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == "application/problem+json"
    assert resposta.json()["instance"] == "acervo-t"


def test_falha_injetada_responde_500(montar):
    cliente, _ = montar(prob_erro=1.0)
    with cliente:
        resposta = cliente.get("/v1/livros/1")
    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "falha injetada pelo laboratório"


def test_correlacao_volta_na_resposta(montar):
    cliente, _ = montar()
    with cliente:
        resposta = cliente.get("/v1/livros/2", headers={cabecalho_correlacao: "c-abc"})
    assert resposta.headers[cabecalho_correlacao] == "c-abc"
    assert resposta.headers["X-Span-ID"]


def test_span_de_servidor_registra_contexto_e_tempos(montar, ler_log):
    cliente, log = montar()
    with cliente:
        cliente.get(
            "/v1/livros/3",
            headers={cabecalho_correlacao: "c-1", cabecalho_mensagem: "m-1", cabecalho_causa: "m-0", cabecalho_span_pai: "s-0"},
        )
    [span] = [e for e in ler_log(log) if e.get("span_kind") == "server"]
    assert span["correlation_id"] == "c-1"
    assert span["message_id"] == "m-1"
    assert span["causation_id"] == "m-0"
    assert span["parent_span_id"] == "s-0"
    assert span["operation"] == "consultar_livro"
    assert span["outcome"] == "success"
    assert span["status"] == 200
    assert span["espera_ms"] >= 0
    assert span["servico_ms"] >= 0
    assert span["duration_ms"] >= span["servico_ms"]


def test_erro_vira_log_de_nivel_error(montar, ler_log):
    cliente, log = montar(prob_erro=1.0)
    with cliente:
        cliente.get("/v1/livros/1")
    [span] = [e for e in ler_log(log) if e.get("span_kind") == "server"]
    assert span["level"] == "ERROR"
    assert span["outcome"] == "server_error"
    assert span["falha_injetada"] is True


def test_lentidao_injetada_aparece_no_tempo_de_servico(montar, ler_log):
    cliente, log = montar(prob_lentidao=1.0, atraso_lento_ms=60)
    with cliente:
        cliente.get("/v1/livros/1")
    [span] = [e for e in ler_log(log) if e.get("span_kind") == "server"]
    assert span["lento"] is True
    assert span["servico_ms"] >= 55


def test_metricas_mostram_fila_e_nao_poluem_o_log(montar, ler_log):
    cliente, log = montar(trabalhadores=3)
    with cliente:
        cliente.get("/v1/livros/1")
        metricas = cliente.get("/v1/metricas").json()
    assert metricas["trabalhadores"] == 3
    assert metricas["atendidas"] == 1
    assert metricas["na_fila"] == 0
    assert not [e for e in ler_log(log) if e.get("path") == "/v1/metricas"]


def test_ciclo_de_vida_registra_inicio_e_fim(montar, ler_log):
    cliente, log = montar()
    with cliente:
        pass
    operacoes = [e["operation"] for e in ler_log(log)]
    assert operacoes == ["iniciar", "encerrar"]
