from typing import Annotated

from fastapi import APIRouter, Header, Query, Response, status

from app import concorrencia
from app.esquemas import Livro, LivroEntrada, LivroParcial, PaginaDeLivros
from app.paginacao import DependenciaDePaginacao, contar_paginas
from app.repositorios import livros as repositorio

roteador = APIRouter(prefix="/v1/livros", tags=["livros"])

CabecalhoIfMatch = Annotated[str | None, Header(alias="If-Match")]
CabecalhoIfNoneMatch = Annotated[str | None, Header(alias="If-None-Match")]


def aplicar_etag(resposta: Response, versao: int) -> None:
    resposta.headers[concorrencia.CABECALHO_ETAG] = concorrencia.gerar_etag(versao)
    resposta.headers[concorrencia.CABECALHO_CACHE] = concorrencia.POLITICA_DE_CACHE


@roteador.get("", response_model=PaginaDeLivros, summary="Listar livros com paginação e filtros")
def listar_livros(
    paginacao: DependenciaDePaginacao,
    autor: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    titulo: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    apenas_disponiveis: Annotated[bool, Query()] = False,
):
    itens, total = repositorio.listar(paginacao, autor, titulo, apenas_disponiveis)
    return PaginaDeLivros(
        itens=itens,
        pagina=paginacao.pagina,
        tamanho=paginacao.tamanho,
        total=total,
        total_de_paginas=contar_paginas(total, paginacao.tamanho),
    )


@roteador.post("", response_model=Livro, status_code=status.HTTP_201_CREATED, summary="Cadastrar livro")
def criar_livro(entrada: LivroEntrada, resposta: Response):
    livro = repositorio.criar(entrada.model_dump())
    resposta.headers["Location"] = f"/v1/livros/{livro['id']}"
    aplicar_etag(resposta, livro["versao"])
    return livro


@roteador.get("/{livro_id}", response_model=Livro, summary="Obter livro")
def obter_livro(livro_id: int, resposta: Response, if_none_match: CabecalhoIfNoneMatch = None):
    livro = repositorio.obter_ou_falhar(livro_id)
    if concorrencia.representacao_inalterada(if_none_match, livro["versao"]):
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                concorrencia.CABECALHO_ETAG: concorrencia.gerar_etag(livro["versao"]),
                concorrencia.CABECALHO_CACHE: concorrencia.POLITICA_DE_CACHE,
            },
        )
    aplicar_etag(resposta, livro["versao"])
    return livro


@roteador.put("/{livro_id}", response_model=Livro, summary="Substituir livro")
def substituir_livro(
    livro_id: int,
    entrada: LivroEntrada,
    resposta: Response,
    if_match: CabecalhoIfMatch = None,
):
    atual = repositorio.obter_ou_falhar(livro_id)
    concorrencia.conferir_if_match(if_match, atual["versao"])
    livro = repositorio.substituir(livro_id, entrada.model_dump())
    aplicar_etag(resposta, livro["versao"])
    return livro


@roteador.patch("/{livro_id}", response_model=Livro, summary="Atualizar livro parcialmente")
def atualizar_livro(
    livro_id: int,
    entrada: LivroParcial,
    resposta: Response,
    if_match: CabecalhoIfMatch = None,
):
    atual = repositorio.obter_ou_falhar(livro_id)
    concorrencia.conferir_if_match(if_match, atual["versao"])
    livro = repositorio.atualizar_parcial(livro_id, entrada.model_dump(exclude_none=True))
    aplicar_etag(resposta, livro["versao"])
    return livro


@roteador.delete("/{livro_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover livro")
def remover_livro(livro_id: int, if_match: CabecalhoIfMatch = None):
    atual = repositorio.obter_ou_falhar(livro_id)
    concorrencia.conferir_if_match(if_match, atual["versao"])
    repositorio.remover(livro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
