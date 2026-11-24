import json

import pytest


@pytest.fixture
def ler_log():
    def ler(caminho):
        return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]

    return ler
