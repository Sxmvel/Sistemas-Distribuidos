import sqlite3
import threading
from pathlib import Path

from app import config
from app.registro import agora_iso

ESQUEMA = """
CREATE TABLE IF NOT EXISTS mensagens (
    message_id  TEXT    PRIMARY KEY,
    producer_id TEXT    NOT NULL,
    sequence    INTEGER NOT NULL,
    topico      TEXT    NOT NULL,
    evento      TEXT    NOT NULL,
    recebido_em TEXT    NOT NULL,
    dup         INTEGER NOT NULL DEFAULT 0,
    retain      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS estoque (
    isbn          TEXT    PRIMARY KEY,
    titulo        TEXT    NOT NULL,
    em_circulacao INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS multas (
    leitor          TEXT    PRIMARY KEY,
    dias            INTEGER NOT NULL DEFAULT 0,
    valor_centavos  INTEGER NOT NULL DEFAULT 0,
    cobrancas       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS terminais (
    terminal      TEXT PRIMARY KEY,
    unidade       TEXT NOT NULL,
    estado        TEXT NOT NULL,
    motivo        TEXT,
    atualizado_em TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mensagens_produtor ON mensagens (producer_id, sequence);
"""

CENTAVOS_POR_DIA = int(round(config.VALOR_DA_MULTA_POR_DIA * 100))


class RepositorioDeAtrasos:
    def __init__(self, caminho=None, reiniciar=False):
        bruto = caminho or config.CAMINHO_DO_BANCO
        self.caminho = bruto if bruto == ":memory:" else Path(bruto)
        if reiniciar and isinstance(self.caminho, Path) and self.caminho.exists():
            self.caminho.unlink()
        self.conexao = sqlite3.connect(self.caminho, check_same_thread=False)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.executescript(ESQUEMA)
        self.conexao.commit()
        self.trava = threading.Lock()

    def registrar_mensagem(self, envelope, topico, evento, dup=False, retain=False):
        with self.trava:
            cursor = self.conexao.execute(
                """
                INSERT OR IGNORE INTO mensagens
                    (message_id, producer_id, sequence, topico, evento, recebido_em, dup, retain)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope.message_id,
                    envelope.producer_id,
                    envelope.sequence,
                    topico,
                    evento,
                    agora_iso(),
                    int(dup),
                    int(retain),
                ),
            )
            self.conexao.commit()
            return cursor.rowcount == 1

    def aplicar_emprestimo(self, envelope):
        dados = envelope.data
        with self.trava:
            self.conexao.execute(
                """
                INSERT INTO estoque (isbn, titulo, em_circulacao)
                VALUES (?, ?, 1)
                ON CONFLICT(isbn) DO UPDATE SET em_circulacao = em_circulacao + 1
                """,
                (dados.get("isbn", "desconhecido"), dados.get("titulo", "?")),
            )
            self.conexao.commit()

    def aplicar_devolucao(self, envelope):
        dados = envelope.data
        dias = int(dados.get("dias_de_atraso", 0) or 0)
        leitor = dados.get("leitor", "desconhecido")
        with self.trava:
            self.conexao.execute(
                """
                INSERT INTO estoque (isbn, titulo, em_circulacao)
                VALUES (?, ?, 0)
                ON CONFLICT(isbn) DO UPDATE SET
                    em_circulacao = MAX(0, em_circulacao - 1)
                """,
                (dados.get("isbn", "desconhecido"), dados.get("titulo", "?")),
            )
            if dias > 0:
                self.conexao.execute(
                    """
                    INSERT INTO multas (leitor, dias, valor_centavos, cobrancas)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(leitor) DO UPDATE SET
                        dias = dias + excluded.dias,
                        valor_centavos = valor_centavos + excluded.valor_centavos,
                        cobrancas = cobrancas + 1
                    """,
                    (leitor, dias, dias * CENTAVOS_POR_DIA),
                )
            self.conexao.commit()
        return dias

    def atualizar_status(self, envelope, terminal):
        dados = envelope.data
        with self.trava:
            self.conexao.execute(
                """
                INSERT INTO terminais (terminal, unidade, estado, motivo, atualizado_em)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(terminal) DO UPDATE SET
                    unidade = excluded.unidade,
                    estado = excluded.estado,
                    motivo = excluded.motivo,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    terminal,
                    dados.get("unidade", "?"),
                    dados.get("estado", "?"),
                    dados.get("motivo"),
                    agora_iso(),
                ),
            )
            self.conexao.commit()

    def _um(self, consulta, *parametros):
        with self.trava:
            return self.conexao.execute(consulta, parametros).fetchone()

    def total_de_mensagens(self):
        return self._um("SELECT COUNT(*) AS total FROM mensagens")["total"]

    def total_por_evento(self, evento):
        return self._um(
            "SELECT COUNT(*) AS total FROM mensagens WHERE evento = ?", evento
        )["total"]

    def multa_de(self, leitor):
        linha = self._um("SELECT * FROM multas WHERE leitor = ?", leitor)
        return dict(linha) if linha else None

    def resumo(self):
        with self.trava:
            multas = self.conexao.execute(
                "SELECT COALESCE(SUM(valor_centavos), 0) AS centavos,"
                " COALESCE(SUM(cobrancas), 0) AS cobrancas FROM multas"
            ).fetchone()
            circulacao = self.conexao.execute(
                "SELECT COALESCE(SUM(em_circulacao), 0) AS total FROM estoque"
            ).fetchone()
            mensagens = self.conexao.execute(
                "SELECT COUNT(*) AS total FROM mensagens"
            ).fetchone()
            terminais = self.conexao.execute(
                "SELECT terminal, estado FROM terminais ORDER BY terminal"
            ).fetchall()
        return {
            "mensagens_persistidas": mensagens["total"],
            "multa_total_reais": round(multas["centavos"] / 100, 2),
            "cobrancas_aplicadas": multas["cobrancas"],
            "exemplares_em_circulacao": circulacao["total"],
            "terminais": {linha["terminal"]: linha["estado"] for linha in terminais},
        }

    def fechar(self):
        with self.trava:
            self.conexao.close()
