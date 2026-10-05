import hashlib
import sqlite3
from datetime import datetime, timezone

from app.db import conexao
from app.erros import ChaveDeIdempotenciaReutilizada, ConflitoDeEstado, RecursoNaoEncontrado

SELECAO = "SELECT id, livro_id, leitor, emprestado_em, devolvido_em FROM emprestimos"


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def listar_do_livro(livro_id: int):
    with conexao() as conn:
        if conn.execute("SELECT 1 FROM livros WHERE id = ?", (livro_id,)).fetchone() is None:
            raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")
        linhas = conn.execute(f"{SELECAO} WHERE livro_id = ? ORDER BY id", (livro_id,)).fetchall()
    return [dict(linha) for linha in linhas]


def obter(emprestimo_id: int):
    with conexao() as conn:
        linha = conn.execute(f"{SELECAO} WHERE id = ?", (emprestimo_id,)).fetchone()
    return dict(linha) if linha else None


def obter_ou_falhar(emprestimo_id: int):
    emprestimo = obter(emprestimo_id)
    if emprestimo is None:
        raise RecursoNaoEncontrado(f"Não existe empréstimo com id {emprestimo_id}.")
    return emprestimo


def inserir(conn, livro_id: int, leitor: str) -> int:
    livro = conn.execute("SELECT exemplares_total FROM livros WHERE id = ?", (livro_id,)).fetchone()
    if livro is None:
        raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")

    ativos = conn.execute(
        "SELECT COUNT(*) FROM emprestimos WHERE livro_id = ? AND devolvido_em IS NULL",
        (livro_id,),
    ).fetchone()[0]
    if ativos >= livro["exemplares_total"]:
        raise ConflitoDeEstado(
            f"Não há exemplares disponíveis do livro {livro_id}: "
            f"{ativos} de {livro['exemplares_total']} estão emprestados."
        )

    cursor = conn.execute(
        "INSERT INTO emprestimos (livro_id, leitor, emprestado_em) VALUES (?, ?, ?)",
        (livro_id, leitor, agora()),
    )
    conn.execute("UPDATE livros SET versao = versao + 1 WHERE id = ?", (livro_id,))
    return cursor.lastrowid


def criar(livro_id: int, leitor: str):
    with conexao() as conn:
        criado = inserir(conn, livro_id, leitor)
    return obter(criado)


def calcular_impressao(livro_id: int, leitor: str) -> str:
    return hashlib.sha256(f"{livro_id}|{leitor}".encode()).hexdigest()


def buscar_pela_chave(conn, chave: str, impressao: str):
    linha = conn.execute(
        "SELECT impressao, emprestimo_id FROM chaves_de_idempotencia WHERE chave = ?", (chave,)
    ).fetchone()
    if linha is None:
        return None
    if linha["impressao"] != impressao:
        raise ChaveDeIdempotenciaReutilizada(
            f"A chave {chave} já foi usada em um pedido diferente. "
            "Gere uma chave nova para cada intenção de empréstimo."
        )
    return linha["emprestimo_id"]


def registrar(livro_id: int, leitor: str, chave: str | None = None):
    if chave is None:
        return criar(livro_id, leitor), False

    impressao = calcular_impressao(livro_id, leitor)
    try:
        with conexao() as conn:
            existente = buscar_pela_chave(conn, chave, impressao)
            if existente is not None:
                return obter(existente), True
            criado = inserir(conn, livro_id, leitor)
            conn.execute(
                "INSERT INTO chaves_de_idempotencia (chave, impressao, emprestimo_id, criada_em) "
                "VALUES (?, ?, ?, ?)",
                (chave, impressao, criado, agora()),
            )
    except sqlite3.IntegrityError:
        with conexao() as conn:
            existente = buscar_pela_chave(conn, chave, impressao)
        if existente is None:
            raise
        return obter(existente), True
    return obter(criado), False


def registrar_devolucao(emprestimo_id: int):
    with conexao() as conn:
        linha = conn.execute(
            "SELECT livro_id, devolvido_em FROM emprestimos WHERE id = ?", (emprestimo_id,)
        ).fetchone()
        if linha is None:
            raise RecursoNaoEncontrado(f"Não existe empréstimo com id {emprestimo_id}.")
        if linha["devolvido_em"] is not None:
            raise ConflitoDeEstado(
                f"O empréstimo {emprestimo_id} já foi devolvido em {linha['devolvido_em']}."
            )

        conn.execute("UPDATE emprestimos SET devolvido_em = ? WHERE id = ?", (agora(), emprestimo_id))
        conn.execute("UPDATE livros SET versao = versao + 1 WHERE id = ?", (linha["livro_id"],))
    return obter(emprestimo_id)
