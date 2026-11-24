import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

raiz = Path(__file__).resolve().parent.parent
pasta_de_logs = raiz / "logs"
python = sys.executable


class FalhaDeOrquestracao(Exception):
    pass


def porta_ocupada(porta):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tomada:
        tomada.settimeout(0.2)
        return tomada.connect_ex(("127.0.0.1", porta)) == 0


class Servico:
    def __init__(self, nome, alvo, porta, ambiente, pasta):
        self.nome = nome
        self.alvo = alvo
        self.porta = porta
        self.ambiente = ambiente
        self.log = Path(pasta) / f"{nome}.jsonl"
        self.saida = Path(pasta) / f"{nome}.stderr.txt"
        self.processo = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}"

    @property
    def vivo(self):
        return self.processo is not None and self.processo.poll() is None

    def iniciar(self, prazo_s=20.0):
        if porta_ocupada(self.porta):
            raise FalhaDeOrquestracao(f"a porta {self.porta} já está em uso; encerre o processo que a ocupa")
        self.log.parent.mkdir(parents=True, exist_ok=True)
        ambiente = {**os.environ, **{k: str(v) for k, v in self.ambiente.items()}, "AP9_LOG": str(self.log), "PYTHONPATH": str(raiz)}
        comando = [
            python, "-m", "uvicorn", self.alvo, "--factory",
            "--host", "127.0.0.1", "--port", str(self.porta),
            "--no-access-log", "--log-level", "warning",
        ]
        with open(self.saida, "a", encoding="utf-8") as saida:
            self.processo = subprocess.Popen(comando, cwd=raiz, env=ambiente, stdout=subprocess.DEVNULL, stderr=saida)
        limite = time.monotonic() + prazo_s
        while time.monotonic() < limite:
            if self.processo.poll() is not None:
                raise FalhaDeOrquestracao(f"{self.nome} terminou ao iniciar; veja {self.saida}")
            try:
                if requests.get(self.url + "/v1/saude", timeout=0.5).status_code == 200:
                    return self
            except requests.RequestException:
                pass
            time.sleep(0.1)
        self.matar()
        raise FalhaDeOrquestracao(f"{self.nome} não respondeu em {prazo_s:.0f} s")

    def matar(self):
        if self.processo is None:
            return
        if self.processo.poll() is None:
            self.processo.kill()
            self.processo.wait(timeout=10)
        limite = time.monotonic() + 5
        while porta_ocupada(self.porta) and time.monotonic() < limite:
            time.sleep(0.05)
