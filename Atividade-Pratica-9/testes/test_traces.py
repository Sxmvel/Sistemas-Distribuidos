import json

from medicao.traces import (
    agrupar_por_correlacao,
    desenhar,
    ler_eventos,
    mensagens_repetidas,
    montar_arvore,
    orfaos,
    tempo_por_servico,
)


def span(span_id, pai, servico, tipo, inicio, duracao, instancia=None, message_id="m", outcome="success", **extras):
    return {
        "service": servico,
        "instance": instancia or f"{servico}-1",
        "correlation_id": "c-1",
        "message_id": message_id,
        "span_id": span_id,
        "parent_span_id": pai,
        "span_kind": tipo,
        "operation": "consultar_livro",
        "start_ms": inicio,
        "duration_ms": duracao,
        "outcome": outcome,
        **extras,
    }


def trace_com_failover():
    return [
        span("b", None, "balcao", "server", 1000, 50, message_id="m-cliente"),
        span("t1", "b", "balcao", "client", 1001, 20, message_id="m-1", outcome="server_error", attempt=1, replica="http://127.0.0.1:8201"),
        span("a1", "t1", "acervo", "server", 1005, 12, instancia="acervo-a", message_id="m-1", outcome="server_error"),
        span("t2", "b", "balcao", "client", 1022, 20, message_id="m-1", attempt=2, replica="http://127.0.0.1:8202"),
        span("a2", "t2", "acervo", "server", 1026, 12, instancia="acervo-b", message_id="m-1"),
    ]


def test_arvore_pendura_cada_span_no_pai():
    [raiz] = montar_arvore(trace_com_failover())
    assert raiz.evento["span_id"] == "b"
    assert [f.evento["span_id"] for f in raiz.filhos] == ["t1", "t2"]
    assert [f.filhos[0].evento["span_id"] for f in raiz.filhos] == ["a1", "a2"]


def test_desenho_tem_uma_linha_por_span_com_deslocamento():
    linhas = desenhar(montar_arvore(trace_com_failover()))
    assert len(linhas) == 5
    assert linhas[0].strip().startswith("+0.0 ms")
    assert "tentativa 2 -> 8202" in linhas[3]
    assert "server_error" in linhas[1]


def test_mesma_mensagem_em_duas_replicas_e_repeticao():
    assert mensagens_repetidas(trace_com_failover()) == {"m-1": ["acervo-a", "acervo-b"]}


def test_orfao_e_span_cujo_pai_nao_aparece_em_log_nenhum():
    eventos = trace_com_failover() + [span("x", "sumiu", "acervo", "server", 2000, 5)]
    assert [s["span_id"] for s in orfaos(eventos)] == ["x"]
    assert orfaos(trace_com_failover()) == []


def test_tempo_por_servico_soma_spans_de_servidor():
    assert tempo_por_servico(trace_com_failover()) == {"balcao": 50, "acervo": 24}


def test_ler_e_agrupar_logs_de_varios_arquivos(tmp_path):
    eventos = trace_com_failover()
    (tmp_path / "balcao.jsonl").write_text("\n".join(json.dumps(e) for e in eventos[:2]) + "\n", encoding="utf-8")
    (tmp_path / "acervo.jsonl").write_text("\n".join(json.dumps(e) for e in eventos[2:]) + "\n\n", encoding="utf-8")
    lidos = ler_eventos(tmp_path / "balcao.jsonl", tmp_path / "acervo.jsonl", tmp_path / "inexistente.jsonl")
    assert len(lidos) == 5
    assert list(agrupar_por_correlacao(lidos)) == ["c-1"]
