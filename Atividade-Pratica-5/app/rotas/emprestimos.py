from fastapi import APIRouter, Response, status

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
)
def registrar_emprestimo(livro_id: int, entrada: EmprestimoEntrada, resposta: Response):
    emprestimo = repositorio.criar(livro_id, entrada.leitor)
    resposta.headers["Location"] = f"/v1/emprestimos/{emprestimo['id']}"
    return emprestimo


@roteador.get("/{emprestimo_id}", response_model=Emprestimo, summary="Obter empréstimo")
def obter_emprestimo(emprestimo_id: int):
    return repositorio.obter_ou_falhar(emprestimo_id)


@roteador.patch("/{emprestimo_id}", response_model=Emprestimo, summary="Registrar devolução")
def atualizar_emprestimo(emprestimo_id: int, entrada: EmprestimoParcial):
    return repositorio.registrar_devolucao(emprestimo_id)
