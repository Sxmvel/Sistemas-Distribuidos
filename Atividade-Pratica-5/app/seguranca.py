import hmac
from typing import Annotated

from fastapi import Depends, Header

from app import config
from app.erros import NaoAutenticado, SemPermissao


def identificar_papel(autorizacao: str | None) -> str:
    if not autorizacao:
        raise NaoAutenticado("Envie o cabeçalho Authorization: Bearer <token>.")

    esquema, _, credencial = autorizacao.partition(" ")
    credencial = credencial.strip()
    if esquema.lower() != "bearer" or not credencial:
        raise NaoAutenticado("O cabeçalho Authorization deve usar o esquema Bearer.")

    recebido = credencial.encode()
    encontrado = None
    for papel, token in config.tokens.items():
        if hmac.compare_digest(recebido, token.encode()):
            encontrado = papel
    if encontrado is None:
        raise NaoAutenticado("Token inválido.")
    return encontrado


def exigir_papel(*permitidos: str):
    def verificar(authorization: Annotated[str | None, Header()] = None) -> str:
        papel = identificar_papel(authorization)
        if papel not in permitidos:
            raise SemPermissao(
                f"O papel {papel} não pode executar esta operação. "
                f"Papéis permitidos: {', '.join(permitidos)}."
            )
        return papel

    return verificar


somente_bibliotecario = Depends(exigir_papel("bibliotecario"))
atendimento = Depends(exigir_papel("bibliotecario", "atendente"))
