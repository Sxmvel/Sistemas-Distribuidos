import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware

CABECALHO_CORRELACAO = "X-Request-ID"
CABECALHO_DURACAO = "X-Duracao-Ms"
CAMINHO_DO_LOG = Path(__file__).resolve().parent.parent / "logs" / "api.jsonl"


def configurar_registrador() -> logging.Logger:
    registrador = logging.getLogger("biblioteca")
    if registrador.handlers:
        return registrador

    CAMINHO_DO_LOG.parent.mkdir(parents=True, exist_ok=True)
    registrador.setLevel(logging.INFO)
    registrador.propagate = False

    formato = logging.Formatter("%(message)s")
    for destino in (logging.StreamHandler(), logging.FileHandler(CAMINHO_DO_LOG, encoding="utf-8")):
        destino.setFormatter(formato)
        registrador.addHandler(destino)

    return registrador


class RegistroDeRequisicoes(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.registrador = configurar_registrador()

    def escrever(self, correlacao, requisicao, status_http, duracao_ms, falha=None):
        evento = {
            "instante": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "correlacao": correlacao,
            "metodo": requisicao.method,
            "caminho": requisicao.url.path,
            "consulta": requisicao.url.query or None,
            "status": status_http,
            "duracao_ms": round(duracao_ms, 2),
            "cliente": requisicao.client.host if requisicao.client else None,
        }
        if falha:
            evento["falha"] = falha
        self.registrador.info(json.dumps(evento, ensure_ascii=False))

    async def dispatch(self, requisicao, chamar_proximo):
        correlacao = requisicao.headers.get(CABECALHO_CORRELACAO) or uuid.uuid4().hex[:12]
        requisicao.state.correlacao = correlacao
        inicio = time.perf_counter()

        try:
            resposta = await chamar_proximo(requisicao)
        except Exception as erro:
            self.escrever(correlacao, requisicao, 500, (time.perf_counter() - inicio) * 1000, type(erro).__name__)
            raise

        duracao_ms = (time.perf_counter() - inicio) * 1000
        resposta.headers[CABECALHO_CORRELACAO] = correlacao
        resposta.headers[CABECALHO_DURACAO] = f"{duracao_ms:.2f}"
        self.escrever(correlacao, requisicao, resposta.status_code, duracao_ms)
        return resposta
