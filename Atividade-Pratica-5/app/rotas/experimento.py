import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app import falhas

roteador = APIRouter(
    prefix="/experimento",
    tags=["experimento"],
    dependencies=[Depends(falhas.exigir_laboratorio)],
)


@roteador.get("/instavel", summary="Rota de laboratório com atraso e falha injetados")
def instavel(
    atraso_ms: Annotated[int, Query(ge=0, le=10000)] = 0,
    prob_falha: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
):
    if atraso_ms > 0:
        time.sleep(atraso_ms / 1000)
    if falhas.deve_falhar(prob_falha):
        raise HTTPException(status_code=503, detail="falha injetada")
    return {"ok": True, "atraso_ms": atraso_ms}
