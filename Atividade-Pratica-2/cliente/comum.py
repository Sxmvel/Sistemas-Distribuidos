import uuid
from dataclasses import dataclass, field

import requests

BASE = "http://127.0.0.1:8000"
TIMEOUT = 3.0
PORTA_SEM_SERVIDOR = 65000


@dataclass
class Evidencia:
    cenario: str
    requisicao: str
    esperado: str
    obtido: str
    sucesso: bool
    analise: str


@dataclass
class Coletor:
    evidencias: list[Evidencia] = field(default_factory=list)

    def registrar(self, cenario, requisicao, esperado, obtido, analise):
        sucesso = str(esperado) == str(obtido)
        self.evidencias.append(
            Evidencia(cenario, requisicao, str(esperado), str(obtido), sucesso, analise)
        )
        marca = "OK " if sucesso else "FALHA"
        print(f"  [{marca}] {requisicao:<54} esperado={esperado:<18} obtido={obtido}")
        return sucesso

    @property
    def total(self):
        return len(self.evidencias)

    @property
    def falhas(self):
        return [evidencia for evidencia in self.evidencias if not evidencia.sucesso]


def requisitar(metodo, caminho, timeout=TIMEOUT, **kwargs):
    return requests.request(metodo, f"{BASE}{caminho}", timeout=timeout, **kwargs)


def novo_isbn():
    return "978" + str(uuid.uuid4().int)[:10]


def livro_de_teste(**sobrescritas):
    base = {
        "titulo": "Livro de Cenário",
        "autor": "Autor de Cenário",
        "isbn": novo_isbn(),
        "ano": 2020,
        "exemplares_total": 1,
    }
    base.update(sobrescritas)
    return base


def criar_livro(**sobrescritas):
    resposta = requisitar("POST", "/v1/livros", json=livro_de_teste(**sobrescritas))
    resposta.raise_for_status()
    return resposta.json(), resposta.headers.get("ETag")


def servidor_no_ar():
    try:
        return requisitar("GET", "/v1/saude", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False
