from fastapi.responses import JSONResponse


def problema(status, titulo, detalhe, instancia, **extras):
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": titulo,
            "status": status,
            "detail": detalhe,
            "instance": instancia,
            **extras,
        },
    )
