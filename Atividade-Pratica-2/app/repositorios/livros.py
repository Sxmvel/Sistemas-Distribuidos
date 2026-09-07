import sqlite3

from app.db import conexao
from app.erros import ConflitoDeEstado, RecursoNaoEncontrado
from app.paginacao import Paginacao

CAMPOS_ATUALIZAVEIS = ("titulo", "autor", "isbn", "ano", "exemplares_total")

EMPRESTIMOS_ATIVOS = """
    SELECT COUNT(*)
    FROM emprestimos e
    WHERE e.livro_id = l.id AND e.devolvido_em IS NULL
"""

SELECAO = f"""
SELECT l.id,
       l.titulo,
       l.autor,
       l.isbn,
       l.ano,
       l.exemplares_total,
       l.versao,
       l.exemplares_total - ({EMPRESTIMOS_ATIVOS}) AS exemplares_disponiveis
FROM livros l
"""


def montar_filtros(autor, titulo, apenas_disponiveis):
    clausulas, parametros = [], []
    if autor:
        clausulas.append("l.autor LIKE ?")
        parametros.append(f"%{autor}%")
    if titulo:
        clausulas.append("l.titulo LIKE ?")
        parametros.append(f"%{titulo}%")
    if apenas_disponiveis:
        clausulas.append(f"l.exemplares_total > ({EMPRESTIMOS_ATIVOS})")
    onde = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""
    return onde, parametros


def listar(paginacao: Paginacao, autor=None, titulo=None, apenas_disponiveis=False):
    onde, parametros = montar_filtros(autor, titulo, apenas_disponiveis)
    with conexao() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM livros l {onde}", parametros).fetchone()[0]
        linhas = conn.execute(
            f"{SELECAO} {onde} ORDER BY l.id LIMIT ? OFFSET ?",
            [*parametros, paginacao.tamanho, paginacao.deslocamento],
        ).fetchall()
    return [dict(linha) for linha in linhas], total


def obter(livro_id: int):
    with conexao() as conn:
        linha = conn.execute(f"{SELECAO} WHERE l.id = ?", (livro_id,)).fetchone()
    return dict(linha) if linha else None


def obter_ou_falhar(livro_id: int):
    livro = obter(livro_id)
    if livro is None:
        raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")
    return livro


def criar(dados: dict):
    with conexao() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO livros (titulo, autor, isbn, ano, exemplares_total) VALUES (?, ?, ?, ?, ?)",
                tuple(dados[campo] for campo in CAMPOS_ATUALIZAVEIS),
            )
        except sqlite3.IntegrityError as erro:
            raise ConflitoDeEstado(f"Já existe um livro cadastrado com o isbn {dados['isbn']}.") from erro
        criado = cursor.lastrowid
    return obter(criado)


def substituir(livro_id: int, dados: dict):
    with conexao() as conn:
        atual = conn.execute(
            f"SELECT {', '.join(CAMPOS_ATUALIZAVEIS)} FROM livros WHERE id = ?", (livro_id,)
        ).fetchone()
        if atual is None:
            raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")

        novos_valores = tuple(dados[campo] for campo in CAMPOS_ATUALIZAVEIS)
        if tuple(atual) != novos_valores:
            atribuicoes = ", ".join(f"{campo} = ?" for campo in CAMPOS_ATUALIZAVEIS)
            try:
                conn.execute(
                    f"UPDATE livros SET {atribuicoes}, versao = versao + 1 WHERE id = ?",
                    [*novos_valores, livro_id],
                )
            except sqlite3.IntegrityError as erro:
                raise ConflitoDeEstado(f"Já existe um livro cadastrado com o isbn {dados['isbn']}.") from erro
    return obter(livro_id)


def atualizar_parcial(livro_id: int, dados: dict):
    pedidos = {campo: valor for campo, valor in dados.items() if campo in CAMPOS_ATUALIZAVEIS}
    with conexao() as conn:
        atual = conn.execute(
            f"SELECT {', '.join(CAMPOS_ATUALIZAVEIS)} FROM livros WHERE id = ?", (livro_id,)
        ).fetchone()
        if atual is None:
            raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")

        mudancas = {campo: valor for campo, valor in pedidos.items() if atual[campo] != valor}
        if mudancas:
            atribuicoes = ", ".join(f"{campo} = ?" for campo in mudancas)
            try:
                conn.execute(
                    f"UPDATE livros SET {atribuicoes}, versao = versao + 1 WHERE id = ?",
                    [*mudancas.values(), livro_id],
                )
            except sqlite3.IntegrityError as erro:
                raise ConflitoDeEstado(f"Já existe um livro cadastrado com o isbn {pedidos['isbn']}.") from erro
    return obter(livro_id)


def remover(livro_id: int) -> None:
    with conexao() as conn:
        if conn.execute("SELECT 1 FROM livros WHERE id = ?", (livro_id,)).fetchone() is None:
            raise RecursoNaoEncontrado(f"Não existe livro com id {livro_id}.")

        ativos = conn.execute(
            "SELECT COUNT(*) FROM emprestimos WHERE livro_id = ? AND devolvido_em IS NULL",
            (livro_id,),
        ).fetchone()[0]
        if ativos:
            raise ConflitoDeEstado(
                f"O livro {livro_id} possui {ativos} empréstimo(s) ativo(s) e não pode ser removido."
            )

        conn.execute("DELETE FROM livros WHERE id = ?", (livro_id,))
