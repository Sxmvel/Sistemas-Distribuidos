import tempfile
from pathlib import Path

import pytest

from app import config

config.PASTA_DE_LOGS = Path(tempfile.gettempdir()) / "ap4-testes-logs"

from app.cliente import Conexao  # noqa: E402
from app.registro import Registrador  # noqa: E402
from app.repositorio import Repositorio  # noqa: E402
from app.servidor import criar_servidor  # noqa: E402
from app.servico import ServicoDeEmprestimos  # noqa: E402

CUSTO_NOS_TESTES = 0.01


@pytest.fixture
def repositorio():
    return Repositorio()


@pytest.fixture
def servico(repositorio):
    return ServicoDeEmprestimos(repositorio, custo_por_codigo=CUSTO_NOS_TESTES)


@pytest.fixture
def servidor_no_ar(repositorio):
    registrador = Registrador("teste-servidor", "servidor", silencioso=True)
    servidor, servico, porta, _, _ = criar_servidor(
        porta=0,
        workers=8,
        repositorio=repositorio,
        registrador=registrador,
        custo_por_codigo=CUSTO_NOS_TESTES,
    )
    servidor.start()
    yield servidor, servico, porta
    servidor.stop(1).wait()
    registrador.fechar()


@pytest.fixture
def conexao(servidor_no_ar):
    _, _, porta = servidor_no_ar
    with Conexao(f"127.0.0.1:{porta}", origem="teste-cliente") as aberta:
        yield aberta
