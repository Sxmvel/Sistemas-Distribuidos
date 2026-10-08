import time

import pytest

from app import config


def test_rota_de_laboratorio_desligada_por_padrao(anonimo, monkeypatch):
    monkeypatch.setattr(config, "laboratorio_ativo", False)

    resposta = anonimo.get("/experimento/instavel")

    assert resposta.status_code == 404


def test_rota_instavel_sem_falha_devolve_200(anonimo, laboratorio):
    resposta = anonimo.get("/experimento/instavel")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True, "atraso_ms": 0}


def test_falha_certa_devolve_503_em_problem_json(anonimo, laboratorio):
    resposta = anonimo.get("/experimento/instavel", params={"prob_falha": 1.0})

    assert resposta.status_code == 503
    assert resposta.headers["Content-Type"] == "application/problem+json"
    assert resposta.json()["detalhe"] == "falha injetada"


def test_atraso_e_aplicado_antes_da_resposta(anonimo, laboratorio):
    inicio = time.perf_counter()
    resposta = anonimo.get("/experimento/instavel", params={"atraso_ms": 200})

    assert resposta.status_code == 200
    assert time.perf_counter() - inicio >= 0.2


@pytest.mark.parametrize(
    "parametros",
    [{"prob_falha": 1.5}, {"prob_falha": -0.1}, {"atraso_ms": -1}, {"atraso_ms": 999999}, {"atraso_ms": "abc"}],
)
def test_parametros_fora_da_faixa_devolvem_422(anonimo, laboratorio, parametros):
    assert anonimo.get("/experimento/instavel", params=parametros).status_code == 422
