from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

TIPO_DE_MIDIA = "application/problem+json"

TITULOS_PADRAO = {
    status.HTTP_400_BAD_REQUEST: "Requisição inválida",
    status.HTTP_404_NOT_FOUND: "Recurso não encontrado",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Método não permitido",
    status.HTTP_409_CONFLICT: "Conflito com o estado atual",
    status.HTTP_412_PRECONDITION_FAILED: "Precondição falhou",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Entrada inválida",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Falha interna",
}


class ErroDeDominio(Exception):
    status_http = status.HTTP_400_BAD_REQUEST
    tipo = "erro-de-dominio"
    titulo = "Erro de domínio"

    def __init__(self, detalhe: str):
        super().__init__(detalhe)
        self.detalhe = detalhe


class RecursoNaoEncontrado(ErroDeDominio):
    status_http = status.HTTP_404_NOT_FOUND
    tipo = "recurso-nao-encontrado"
    titulo = "Recurso não encontrado"


class ConflitoDeEstado(ErroDeDominio):
    status_http = status.HTTP_409_CONFLICT
    tipo = "conflito-de-estado"
    titulo = "Conflito com o estado atual"


class PrecondicaoFalhou(ErroDeDominio):
    status_http = status.HTTP_412_PRECONDITION_FAILED
    tipo = "precondicao-falhou"
    titulo = "Precondição falhou"


def montar_problema(requisicao: Request, status_http: int, tipo: str, titulo: str, detalhe: str, extras=None):
    problema = {
        "tipo": tipo,
        "titulo": titulo,
        "status": status_http,
        "detalhe": detalhe,
        "instancia": requisicao.url.path,
        "correlacao": getattr(requisicao.state, "correlacao", None),
    }
    if extras:
        problema.update(extras)
    return problema


def responder_problema(requisicao: Request, status_http: int, tipo: str, titulo: str, detalhe: str, extras=None):
    return JSONResponse(
        status_code=status_http,
        content=montar_problema(requisicao, status_http, tipo, titulo, detalhe, extras),
        media_type=TIPO_DE_MIDIA,
    )


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroDeDominio)
    async def tratar_erro_de_dominio(requisicao: Request, erro: ErroDeDominio):
        return responder_problema(requisicao, erro.status_http, erro.tipo, erro.titulo, erro.detalhe)

    @app.exception_handler(RequestValidationError)
    async def tratar_entrada_invalida(requisicao: Request, erro: RequestValidationError):
        campos = [
            {
                "campo": ".".join(str(parte) for parte in falha["loc"][1:]) or "corpo",
                "mensagem": falha["msg"],
            }
            for falha in erro.errors()
        ]
        return responder_problema(
            requisicao,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "entrada-invalida",
            TITULOS_PADRAO[status.HTTP_422_UNPROCESSABLE_CONTENT],
            "A representação enviada é sintaticamente válida, mas não passou na validação.",
            {"campos": campos},
        )

    @app.exception_handler(HTTPException)
    async def tratar_excecao_http(requisicao: Request, erro: HTTPException):
        return responder_problema(
            requisicao,
            erro.status_code,
            "erro-http",
            TITULOS_PADRAO.get(erro.status_code, "Erro"),
            str(erro.detail),
        )

    @app.exception_handler(Exception)
    async def tratar_falha_inesperada(requisicao: Request, erro: Exception):
        return responder_problema(
            requisicao,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "falha-interna",
            TITULOS_PADRAO[status.HTTP_500_INTERNAL_SERVER_ERROR],
            "Ocorreu uma falha inesperada. Consulte o log pelo identificador de correlação.",
        )
