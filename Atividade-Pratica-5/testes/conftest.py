import itertools

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import app

contador = itertools.count(1)


def cabecalho_de(papel):
    return {"Authorization": f"Bearer {config.tokens[papel]}"}


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.db")


@pytest.fixture
def cliente(banco_temporario):
    with TestClient(app, headers=cabecalho_de("bibliotecario")) as testador:
        yield testador


@pytest.fixture
def anonimo(banco_temporario):
    with TestClient(app) as testador:
        yield testador


@pytest.fixture
def laboratorio(monkeypatch):
    monkeypatch.setattr(config, "laboratorio_ativo", True)


@pytest.fixture
def dados_de_livro():
    def construir(**sobrescritas):
        base = {
            "titulo": "Dom Casmurro",
            "autor": "Machado de Assis",
            "isbn": f"978{next(contador):010d}",
            "ano": 1899,
            "exemplares_total": 2,
        }
        base.update(sobrescritas)
        return base

    return construir


@pytest.fixture
def livro(cliente, dados_de_livro):
    resposta = cliente.post("/v1/livros", json=dados_de_livro())
    assert resposta.status_code == 201
    return resposta.json()
