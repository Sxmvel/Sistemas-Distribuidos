from observabilidade.contexto import (
    ContextoDeRequisicao,
    cabecalho_causa,
    cabecalho_correlacao,
    cabecalho_mensagem,
    cabecalho_span_pai,
)
from observabilidade.registro import RegistradorEstruturado


def test_contexto_reaproveita_identificadores_recebidos():
    contexto = ContextoDeRequisicao.dos_cabecalhos({cabecalho_correlacao: "c-1", cabecalho_mensagem: "m-1", cabecalho_span_pai: "s-0"})
    assert contexto.correlation_id == "c-1"
    assert contexto.message_id == "m-1"
    assert contexto.parent_span_id == "s-0"
    assert contexto.span_id not in (None, "s-0")


def test_contexto_gera_identificadores_ausentes():
    contexto = ContextoDeRequisicao.dos_cabecalhos({})
    assert len(contexto.correlation_id) == 32
    assert len(contexto.message_id) == 16
    assert contexto.causation_id is None
    assert contexto.parent_span_id is None


def test_cabecalhos_para_dependencia_encadeiam_a_causa():
    contexto = ContextoDeRequisicao.dos_cabecalhos({cabecalho_correlacao: "c-1", cabecalho_mensagem: "m-1"})
    cabecalhos = contexto.cabecalhos_para_dependencia("m-2", "s-2")
    assert cabecalhos == {cabecalho_correlacao: "c-1", cabecalho_mensagem: "m-2", cabecalho_causa: "m-1", cabecalho_span_pai: "s-2"}


def test_log_estruturado_tem_campos_em_ordem_e_omite_nulos(tmp_path, ler_log):
    caminho = tmp_path / "api.jsonl"
    registrador = RegistradorEstruturado("api", "api-1", caminho)
    registrador.registrar(operation="criar_pedido", outcome="success", correlation_id="c-18f2", duration_ms=83, error=None, extra="x")
    registrador.fechar()
    [evento] = ler_log(caminho)
    assert list(evento)[:4] == ["timestamp", "level", "service", "instance"]
    assert evento["service"] == "api"
    assert evento["operation"] == "criar_pedido"
    assert evento["duration_ms"] == 83
    assert evento["outcome"] == "success"
    assert evento["extra"] == "x"
    assert "error" not in evento
    assert list(evento).index("outcome") < list(evento).index("extra")


def test_registrador_sem_arquivo_nao_falha():
    registrador = RegistradorEstruturado("api", "api-1")
    evento = registrador.registrar(operation="x", outcome="success")
    assert evento["instance"] == "api-1"
