import pytest

from app import topicos
from app.envelope import Envelope
from app.persistencia import RepositorioDeAtrasos

LEITOR = "ana.souza"


@pytest.fixture
def repositorio(tmp_path):
    repositorio = RepositorioDeAtrasos(tmp_path / "atrasos.db", reiniciar=True)
    yield repositorio
    repositorio.fechar()


def devolucao(dias, sequence=1):
    return Envelope.novo(
        producer_id="term-01",
        sequence=sequence,
        data={
            "acao": topicos.DEVOLUCAO,
            "isbn": "9788535910663",
            "titulo": "Dom Casmurro",
            "leitor": LEITOR,
            "dias_de_atraso": dias,
        },
    )


def emprestimo(sequence=1):
    return Envelope.novo(
        producer_id="term-01",
        sequence=sequence,
        data={
            "acao": topicos.EMPRESTIMO,
            "isbn": "9788535910663",
            "titulo": "Dom Casmurro",
            "leitor": LEITOR,
            "prazo_dias": 14,
        },
    )


def aplicar(repositorio, envelope, evento, deduplicar=True):
    novo = repositorio.registrar_mensagem(envelope, "biblioteca/central/term-01/x", evento)
    if deduplicar and not novo:
        return False
    if evento == topicos.EMPRESTIMO:
        repositorio.aplicar_emprestimo(envelope)
    else:
        repositorio.aplicar_devolucao(envelope)
    return True


def test_primeira_entrega_do_message_id_e_nova(repositorio):
    envelope = emprestimo()
    assert repositorio.registrar_mensagem(envelope, "t", topicos.EMPRESTIMO) is True


def test_segunda_entrega_do_mesmo_message_id_nao_e_nova(repositorio):
    envelope = emprestimo()
    repositorio.registrar_mensagem(envelope, "t", topicos.EMPRESTIMO)
    assert repositorio.registrar_mensagem(envelope, "t", topicos.EMPRESTIMO) is False


def test_message_ids_diferentes_com_mesmo_conteudo_sao_eventos_distintos(repositorio):
    assert repositorio.registrar_mensagem(emprestimo(), "t", topicos.EMPRESTIMO) is True
    assert repositorio.registrar_mensagem(emprestimo(), "t", topicos.EMPRESTIMO) is True
    assert repositorio.total_de_mensagens() == 2


def test_multa_e_cobrada_uma_vez_por_devolucao_atrasada(repositorio):
    aplicar(repositorio, devolucao(dias=4), topicos.DEVOLUCAO)
    multa = repositorio.multa_de(LEITOR)
    assert multa["dias"] == 4
    assert multa["valor_centavos"] == 200
    assert multa["cobrancas"] == 1


def test_reprocessar_com_deduplicacao_nao_cobra_de_novo(repositorio):
    envelope = devolucao(dias=4)
    assert aplicar(repositorio, envelope, topicos.DEVOLUCAO) is True
    assert aplicar(repositorio, envelope, topicos.DEVOLUCAO) is False
    multa = repositorio.multa_de(LEITOR)
    assert multa["valor_centavos"] == 200
    assert multa["cobrancas"] == 1


def test_reprocessar_sem_deduplicacao_cobra_em_dobro(repositorio):
    envelope = devolucao(dias=4)
    aplicar(repositorio, envelope, topicos.DEVOLUCAO, deduplicar=False)
    aplicar(repositorio, envelope, topicos.DEVOLUCAO, deduplicar=False)
    multa = repositorio.multa_de(LEITOR)
    assert multa["valor_centavos"] == 400
    assert multa["cobrancas"] == 2


def test_devolucao_em_dia_nao_gera_multa(repositorio):
    aplicar(repositorio, devolucao(dias=0), topicos.DEVOLUCAO)
    assert repositorio.multa_de(LEITOR) is None


def test_emprestimo_e_devolucao_equilibram_a_circulacao(repositorio):
    aplicar(repositorio, emprestimo(sequence=1), topicos.EMPRESTIMO)
    aplicar(repositorio, emprestimo(sequence=2), topicos.EMPRESTIMO)
    assert repositorio.resumo()["exemplares_em_circulacao"] == 2
    aplicar(repositorio, devolucao(dias=0, sequence=3), topicos.DEVOLUCAO)
    assert repositorio.resumo()["exemplares_em_circulacao"] == 1


def test_circulacao_nunca_fica_negativa(repositorio):
    aplicar(repositorio, devolucao(dias=0, sequence=1), topicos.DEVOLUCAO)
    assert repositorio.resumo()["exemplares_em_circulacao"] == 0


def test_status_e_idempotente_por_construcao(repositorio):
    primeiro = Envelope.novo(
        producer_id="term-01",
        sequence=0,
        data={"estado": "online", "motivo": "terminal-em-operacao", "unidade": "central"},
    )
    segundo = Envelope.novo(
        producer_id="term-01",
        sequence=0,
        data={"estado": "offline", "motivo": "desconexao-anormal", "unidade": "central"},
    )
    repositorio.atualizar_status(primeiro, "term-01")
    repositorio.atualizar_status(segundo, "term-01")
    repositorio.atualizar_status(segundo, "term-01")
    assert repositorio.resumo()["terminais"] == {"term-01": "offline"}


def test_resumo_agrega_mensagens_e_multas(repositorio):
    aplicar(repositorio, emprestimo(sequence=1), topicos.EMPRESTIMO)
    aplicar(repositorio, devolucao(dias=2, sequence=2), topicos.DEVOLUCAO)
    resumo = repositorio.resumo()
    assert resumo["mensagens_persistidas"] == 2
    assert resumo["multa_total_reais"] == 1.0
    assert resumo["cobrancas_aplicadas"] == 1


def test_contagem_por_evento(repositorio):
    aplicar(repositorio, emprestimo(sequence=1), topicos.EMPRESTIMO)
    aplicar(repositorio, emprestimo(sequence=2), topicos.EMPRESTIMO)
    aplicar(repositorio, devolucao(dias=0, sequence=3), topicos.DEVOLUCAO)
    assert repositorio.total_por_evento(topicos.EMPRESTIMO) == 2
    assert repositorio.total_por_evento(topicos.DEVOLUCAO) == 1
