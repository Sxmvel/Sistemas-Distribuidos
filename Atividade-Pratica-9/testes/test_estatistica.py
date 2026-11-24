import pytest

from medicao.carga import Amostra
from medicao.estatistica import fracao_acima, linha_do_tempo, percentil, percentil_do_material, resumir


def amostra(indice, inicio_s, duracao_ms, classe="sucesso", detalhe="http_200"):
    status = int(detalhe.removeprefix("http_")) if detalhe.startswith("http_") else None
    return Amostra(indice, inicio_s, duracao_ms, classe, status, detalhe, f"c{indice}", False)


def test_percentil_por_posto_mais_proximo():
    valores = list(range(1, 101))
    assert percentil(valores, 50) == 50
    assert percentil(valores, 95) == 95
    assert percentil(valores, 99) == 99
    assert percentil(valores, 100) == 100


def test_percentil_do_material_escolhe_posicao_acima():
    valores = list(range(1, 101))
    assert percentil_do_material(valores, 50) == 51
    assert percentil_do_material(valores, 99) == 100


def test_percentil_de_lista_vazia():
    assert percentil([], 50) is None
    assert percentil_do_material([], 50) is None


def test_percentil_com_poucas_amostras_usa_o_maximo_para_cauda():
    assert percentil([10, 20, 30], 99) == 30
    assert percentil([10, 20, 30], 1) == 10


def test_resumo_separa_erro_de_aplicacao_de_transporte():
    amostras = [
        amostra(0, 0.0, 10),
        amostra(1, 0.1, 20),
        amostra(2, 0.2, 30, "erro_aplicacao", "http_503"),
        amostra(3, 0.3, 2000, "erro_transporte", "conexao_recusada"),
    ]
    resumo = resumir(amostras)
    assert resumo["n"] == 4
    assert resumo["sucessos"] == 2
    assert resumo["erros_aplicacao"] == 1
    assert resumo["erros_transporte"] == 1
    assert resumo["taxa_de_erro"] == 0.5
    assert resumo["erros_por_tipo"] == {"http_503": 1, "conexao_recusada": 1}


def test_latencia_considera_so_sucessos():
    amostras = [amostra(0, 0.0, 10), amostra(1, 0.0, 5000, "erro_transporte", "timeout_leitura")]
    resumo = resumir(amostras)
    assert resumo["media_ms"] == 10
    assert resumo["max_ms"] == 10


def test_vazao_usa_a_janela_das_amostras():
    amostras = [amostra(i, i * 0.1, 100) for i in range(10)]
    resumo = resumir(amostras)
    assert resumo["duracao_s"] == pytest.approx(1.0)
    assert resumo["vazao_rps"] == pytest.approx(10.0)


def test_disponibilidade_conta_sucesso_dentro_do_objetivo():
    amostras = [amostra(0, 0, 50), amostra(1, 0, 150), amostra(2, 0, 50, "erro_aplicacao", "http_500"), amostra(3, 0, 80)]
    assert resumir(amostras, slo_ms=100)["disponibilidade"] == 0.5


def test_fracao_acima():
    amostras = [amostra(i, 0, d) for i, d in enumerate([10, 20, 300, 400])]
    assert fracao_acima(amostras, 250) == 0.5
    assert fracao_acima([], 250) is None


def test_linha_do_tempo_agrupa_por_segundo():
    amostras = [amostra(0, 0.1, 10), amostra(1, 0.9, 10), amostra(2, 1.5, 10, "erro_aplicacao", "http_503")]
    baldes = linha_do_tempo(amostras, 1.0)
    assert [b["n"] for b in baldes] == [2, 1]
    assert baldes[1]["erros_aplicacao"] == 1
