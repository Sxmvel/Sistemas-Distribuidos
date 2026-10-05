from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query

TAMANHO_PADRAO = 10
TAMANHO_MAXIMO = 100


@dataclass(frozen=True)
class Paginacao:
    pagina: int
    tamanho: int

    @property
    def deslocamento(self) -> int:
        return (self.pagina - 1) * self.tamanho


def obter_paginacao(
    pagina: Annotated[int, Query(ge=1, description="Número da página, começando em 1.")] = 1,
    tamanho: Annotated[
        int,
        Query(ge=1, le=TAMANHO_MAXIMO, description=f"Itens por página (máximo {TAMANHO_MAXIMO})."),
    ] = TAMANHO_PADRAO,
) -> Paginacao:
    return Paginacao(pagina=pagina, tamanho=tamanho)


def contar_paginas(total: int, tamanho: int) -> int:
    return (total + tamanho - 1) // tamanho


DependenciaDePaginacao = Annotated[Paginacao, Depends(obter_paginacao)]
