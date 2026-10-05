import os
from pathlib import Path

raiz_do_projeto = Path(__file__).resolve().parent.parent
pasta_de_logs = raiz_do_projeto / "logs"
pasta_de_docs = raiz_do_projeto / "docs"

caminho_do_banco = Path(os.getenv("BIBLIOTECA_BANCO", raiz_do_projeto / "biblioteca.db"))
caminho_do_log = Path(os.getenv("BIBLIOTECA_LOG", pasta_de_logs / "api.jsonl"))
identificador_do_processo = os.getenv("BIBLIOTECA_PROCESSO", "api")

laboratorio_ativo = os.getenv("BIBLIOTECA_LABORATORIO", "0") == "1"
atraso_na_escrita = float(os.getenv("BIBLIOTECA_ATRASO_NA_ESCRITA", "0"))
semente_das_falhas = os.getenv("BIBLIOTECA_SEMENTE")

tokens = {
    "bibliotecario": os.getenv("BIBLIOTECA_TOKEN_BIBLIOTECARIO", "lab-bibliotecario-troque-me"),
    "atendente": os.getenv("BIBLIOTECA_TOKEN_ATENDENTE", "lab-atendente-troque-me"),
    "consulta": os.getenv("BIBLIOTECA_TOKEN_CONSULTA", "lab-consulta-troque-me"),
}
