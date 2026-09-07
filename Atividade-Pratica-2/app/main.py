from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db, erros
from app.observabilidade import RegistroDeRequisicoes
from app.rotas import diagnostico, emprestimos, livros

DESCRICAO = """
API REST de gerenciamento de acervo de biblioteca.

Duas coleções relacionadas: **livros** e os **empréstimos** de cada livro.

Recursos demonstrados: semântica HTTP, validação de entrada, tratamento explícito
de erros em `application/problem+json`, concorrência otimista com `ETag`/`If-Match`,
validação condicional com `If-None-Match`, paginação com limite e log estruturado
com identificador de correlação.
"""


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    db.inicializar()
    yield


app = FastAPI(
    title="API de Biblioteca",
    version="1.0",
    description=DESCRICAO,
    lifespan=ciclo_de_vida,
)

app.add_middleware(RegistroDeRequisicoes)
erros.registrar_tratadores(app)

app.include_router(livros.roteador)
app.include_router(emprestimos.roteador_aninhado)
app.include_router(emprestimos.roteador)
app.include_router(diagnostico.roteador)
