import json
import shutil
import threading
from datetime import datetime, timezone

from app import config


def agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def caminho_do_log(processo):
    return config.PASTA_DE_LOGS / f"{processo}.jsonl"


def limpar_logs():
    if config.PASTA_DE_LOGS.exists():
        shutil.rmtree(config.PASTA_DE_LOGS)
    config.PASTA_DE_LOGS.mkdir(parents=True, exist_ok=True)


def ler_log(processo):
    caminho = caminho_do_log(processo)
    if not caminho.exists():
        return []
    eventos = []
    with caminho.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                eventos.append(json.loads(linha))
    return eventos


class Registrador:
    def __init__(self, processo, papel, silencioso=False):
        self.processo = processo
        self.papel = papel
        self.silencioso = silencioso
        config.PASTA_DE_LOGS.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho_do_log(processo)
        self._arquivo = self.caminho.open("a", encoding="utf-8")
        self._trava = threading.Lock()

    def evento(self, acao, **campos):
        registro = {
            "instante": agora_iso(),
            "processo": self.processo,
            "papel": self.papel,
            "acao": acao,
        }
        registro.update(campos)
        linha = json.dumps(registro, ensure_ascii=False)
        with self._trava:
            self._arquivo.write(linha + "\n")
            self._arquivo.flush()
        if not self.silencioso:
            print(self.resumir(registro), flush=True)
        return registro

    def resumir(self, registro):
        partes = [f"[{self.processo}]", registro["acao"]]
        for chave in ("topico", "sequence", "qos", "tipo", "estado", "detalhe"):
            if registro.get(chave) is not None:
                partes.append(f"{chave}={registro[chave]}")
        if registro.get("dup"):
            partes.append("dup=1")
        if registro.get("retain"):
            partes.append("retain=1")
        return " ".join(str(parte) for parte in partes)

    def fechar(self):
        with self._trava:
            if not self._arquivo.closed:
                self._arquivo.close()
