import json

import pytest

from app.envelope import (
    SEQUENCIA_DO_TESTAMENTO,
    Envelope,
    EnvelopeInvalido,
    RastreadorDeSequencia,
    Sequenciador,
)

DADOS = {"acao": "emprestimo", "isbn": "9788535910663", "leitor": "ana.souza"}


def envelope_de_teste(**sobrescritas):
    base = {"producer_id": "term-01", "sequence": 1, "data": DADOS}
    base.update(sobrescritas)
    return Envelope.novo(**base)


def test_envelope_novo_preenche_identidade_e_instante():
    envelope = envelope_de_teste()
    assert len(envelope.message_id) == 32
    assert envelope.producer_id == "term-01"
    assert envelope.sequence == 1
    assert envelope.schema_version == 1
    assert envelope.timestamp.endswith("+00:00")


def test_message_id_e_unico_por_envelope():
    identificadores = {envelope_de_teste().message_id for _ in range(50)}
    assert len(identificadores) == 50


def test_ida_e_volta_preserva_o_conteudo():
    original = envelope_de_teste(sequence=42)
    recuperado = Envelope.de_bytes(original.para_bytes())
    assert recuperado == original


def test_payload_que_nao_e_json_e_rejeitado():
    with pytest.raises(EnvelopeInvalido, match="não é JSON válido"):
        Envelope.de_bytes(b"isto nao e json")


def test_payload_que_nao_e_objeto_e_rejeitado():
    with pytest.raises(EnvelopeInvalido, match="objeto JSON"):
        Envelope.de_bytes(b"[1, 2, 3]")


@pytest.mark.parametrize(
    "campo",
    ["message_id", "producer_id", "sequence", "schema_version", "timestamp", "data"],
)
def test_campo_ausente_e_rejeitado(campo):
    conteudo = json.loads(envelope_de_teste().para_bytes())
    del conteudo[campo]
    with pytest.raises(EnvelopeInvalido, match="campos ausentes"):
        Envelope.de_bytes(json.dumps(conteudo).encode())


@pytest.mark.parametrize("sequencia", [-1, "1", 1.5, True, None])
def test_sequencia_invalida_e_rejeitada(sequencia):
    conteudo = json.loads(envelope_de_teste().para_bytes())
    conteudo["sequence"] = sequencia
    with pytest.raises(EnvelopeInvalido, match="sequence"):
        Envelope.de_bytes(json.dumps(conteudo).encode())


def test_esquema_futuro_e_rejeitado_em_vez_de_ignorado():
    conteudo = json.loads(envelope_de_teste().para_bytes())
    conteudo["schema_version"] = 99
    with pytest.raises(EnvelopeInvalido, match="schema_version"):
        Envelope.de_bytes(json.dumps(conteudo).encode())


def test_data_precisa_ser_objeto():
    conteudo = json.loads(envelope_de_teste().para_bytes())
    conteudo["data"] = "temperatura=24"
    with pytest.raises(EnvelopeInvalido, match="data precisa ser"):
        Envelope.de_bytes(json.dumps(conteudo).encode())


def test_sequencia_zero_identifica_o_testamento():
    testamento = envelope_de_teste(sequence=SEQUENCIA_DO_TESTAMENTO)
    assert testamento.e_testamento
    assert not envelope_de_teste(sequence=1).e_testamento


def test_atraso_usa_o_instante_de_producao():
    envelope = envelope_de_teste()
    assert envelope.atraso_ms() >= 0


def test_atraso_com_timestamp_corrompido_devolve_nulo():
    conteudo = json.loads(envelope_de_teste().para_bytes())
    conteudo["timestamp"] = "ontem"
    assert Envelope.de_bytes(json.dumps(conteudo).encode()).atraso_ms() is None


def test_sequenciador_comeca_em_um_e_nao_repete():
    sequenciador = Sequenciador()
    assert [sequenciador.proximo() for _ in range(3)] == [1, 2, 3]
    assert sequenciador.atual == 3


class TestRastreadorDeSequencia:
    def test_primeira_mensagem_do_produtor(self):
        rastreador = RastreadorDeSequencia()
        assert rastreador.classificar("term-01", 1) == ("primeira", 0)

    def test_sequencia_continua_esta_em_ordem(self):
        rastreador = RastreadorDeSequencia()
        rastreador.classificar("term-01", 1)
        assert rastreador.classificar("term-01", 2) == ("em-ordem", 0)

    def test_salto_reporta_o_tamanho_da_lacuna(self):
        rastreador = RastreadorDeSequencia()
        rastreador.classificar("term-01", 1)
        assert rastreador.classificar("term-01", 5) == ("lacuna", 3)

    def test_mesma_sequencia_duas_vezes_e_repetida(self):
        rastreador = RastreadorDeSequencia()
        rastreador.classificar("term-01", 1)
        assert rastreador.classificar("term-01", 1) == ("repetida", 0)

    def test_sequencia_menor_apos_salto_esta_fora_de_ordem(self):
        rastreador = RastreadorDeSequencia()
        rastreador.classificar("term-01", 1)
        rastreador.classificar("term-01", 4)
        assert rastreador.classificar("term-01", 2) == ("fora-de-ordem", 0)

    def test_faltantes_lista_apenas_os_buracos(self):
        rastreador = RastreadorDeSequencia()
        for sequencia in (1, 2, 5):
            rastreador.classificar("term-01", sequencia)
        assert rastreador.faltantes("term-01") == [3, 4]

    def test_produtores_sao_contados_de_forma_independente(self):
        rastreador = RastreadorDeSequencia()
        rastreador.classificar("term-01", 7)
        assert rastreador.classificar("term-03", 1) == ("primeira", 0)
        assert rastreador.faltantes("term-03") == []
