from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db, erros
from app.observabilidade import RegistroDeRequisicoes
from app.rotas import diagnostico, emprestimos, experimento, livros

DESCRICAO = """
API REST de gerenciamento de acervo de biblioteca, usada como alvo dos experimentos de falha da AP5.

Duas coleções relacionadas: **livros** e os **empréstimos** de cada livro.

Recursos demonstrados: semântica HTTP, validação de entrada, tratamento explícito
de erros em `application/problem+json`, concorrência otimista com `ETag`/`If-Match`,
paginação com limite, log estruturado com identificador de correlação, autenticação
por token Bearer com autorização por papel, chave de idempotência em empréstimos e
rotas de laboratório para injeção controlada de atraso e falha.
"""


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    db.inicializar()
    yield


app = FastAPI(
    title="API de Biblioteca",
    version="1.1",
    description=DESCRICAO,
    lifespan=ciclo_de_vida,
)

app.add_middleware(RegistroDeRequisicoes)
erros.registrar_tratadores(app)

app.include_router(livros.roteador)
app.include_router(emprestimos.roteador_aninhado)
app.include_router(emprestimos.roteador)
app.include_router(diagnostico.roteador)
app.include_router(experimento.roteador)
