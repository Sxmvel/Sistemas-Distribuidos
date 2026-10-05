from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from app import falhas, seguranca
from app.esquemas import Emprestimo, EmprestimoEntrada, EmprestimoParcial
from app.repositorios import emprestimos as repositorio

roteador_aninhado = APIRouter(prefix="/v1/livros", tags=["emprestimos"])
roteador = APIRouter(prefix="/v1/emprestimos", tags=["emprestimos"])


@roteador_aninhado.get(
    "/{livro_id}/emprestimos",
    response_model=list[Emprestimo],
    summary="Listar empréstimos de um livro",
)
def listar_emprestimos_do_livro(livro_id: int):
    return repositorio.listar_do_livro(livro_id)


@roteador_aninhado.post(
    "/{livro_id}/emprestimos",
    response_model=Emprestimo,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar empréstimo de um livro",
    dependencies=[seguranca.atendimento],
)
def registrar_emprestimo(
    livro_id: int,
    entrada: EmprestimoEntrada,
    resposta: Response,
    chave: Annotated[str | None, Header(alias="Idempotency-Key", min_length=8, max_length=80)] = None,
):
    emprestimo, reaproveitado = repositorio.registrar(livro_id, entrada.leitor, chave)
    falhas.atrasar_escrita()
    resposta.headers["Location"] = f"/v1/emprestimos/{emprestimo['id']}"
    if reaproveitado:
        resposta.headers["Idempotent-Replayed"] = "true"
    return emprestimo


@roteador.get("/{emprestimo_id}", response_model=Emprestimo, summary="Obter empréstimo")
def obter_emprestimo(emprestimo_id: int):
    return repositorio.obter_ou_falhar(emprestimo_id)


@roteador.patch(
    "/{emprestimo_id}",
    response_model=Emprestimo,
    summary="Registrar devolução",
    dependencies=[seguranca.atendimento],
)
def atualizar_emprestimo(emprestimo_id: int, entrada: EmprestimoParcial):
    return repositorio.registrar_devolucao(emprestimo_id)
