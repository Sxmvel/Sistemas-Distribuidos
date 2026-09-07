import itertools

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

contador = itertools.count(1)


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.db")
    with TestClient(app) as testador:
        yield testador


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
