import os
from pathlib import Path

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent

BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORTA = int(os.getenv("MQTT_PORTA", "1883"))
KEEPALIVE_PADRAO = 30

QOS_PADRAO = 1
VERSAO_DO_ESQUEMA = 1
EXPIRACAO_DA_SESSAO = 300

PASTA_DE_LOGS = RAIZ_DO_PROJETO / "logs"
CAMINHO_DO_BANCO = RAIZ_DO_PROJETO / "atrasos.db"

VALOR_DA_MULTA_POR_DIA = 0.50

PAINEL_ACERVO = "painel-acervo"
SERVICO_ATRASOS = "servico-atrasos"
