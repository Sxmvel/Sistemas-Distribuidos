import asyncio
import os
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.db import conexao

roteador = APIRouter(prefix="/v1", tags=["diagnostico"])


@roteador.get("/saude", summary="Verificar disponibilidade do serviço")
def verificar_saude(resposta: Response):
    if os.getenv("BIBLIOTECA_MANUTENCAO") == "1":
        resposta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        resposta.headers["Retry-After"] = "30"
        return {"status": "indisponivel", "motivo": "servico em manutencao"}

    try:
        with conexao() as conn:
            conn.execute("SELECT 1")
    except Exception:
        resposta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        resposta.headers["Retry-After"] = "30"
        return {"status": "indisponivel", "motivo": "banco de dados inacessivel"}

    return {"status": "ok", "banco": "acessivel"}


@roteador.get("/lento", summary="Rota lenta para experimentos de timeout")
async def responder_devagar(segundos: Annotated[float, Query(ge=0, le=10)] = 2.0):
    await asyncio.sleep(segundos)
    return {"dormiu_por": segundos}


@roteador.get("/indisponivel", summary="Rota que sempre responde 503")
def sempre_indisponivel(resposta: Response):
    resposta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    resposta.headers["Retry-After"] = "5"
    return {"status": "indisponivel", "motivo": "endpoint de laboratorio"}
