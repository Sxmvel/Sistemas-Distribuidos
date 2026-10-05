import sqlite3
from contextlib import contextmanager
from pathlib import Path

CAMINHO_BANCO = Path(__file__).resolve().parent.parent / "biblioteca.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS livros (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT    NOT NULL,
    autor            TEXT    NOT NULL,
    isbn             TEXT    NOT NULL UNIQUE,
    ano              INTEGER NOT NULL,
    exemplares_total INTEGER NOT NULL,
    versao           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS emprestimos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    livro_id      INTEGER NOT NULL REFERENCES livros(id) ON DELETE CASCADE,
    leitor        TEXT    NOT NULL,
    emprestado_em TEXT    NOT NULL,
    devolvido_em  TEXT
);

CREATE INDEX IF NOT EXISTS idx_emprestimos_livro ON emprestimos (livro_id);
"""


@contextmanager
def conexao():
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar():
    with conexao() as conn:
        conn.executescript(ESQUEMA)


def limpar():
    with conexao() as conn:
        conn.execute("DELETE FROM emprestimos")
        conn.execute("DELETE FROM livros")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('livros', 'emprestimos')")
