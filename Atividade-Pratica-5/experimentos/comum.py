import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

import requests

from app import config
from cliente.resiliencia import requisitar

python = sys.executable
no_windows = os.name == "nt"

tokens = {papel: f"{papel}-{secrets.token_urlsafe(12)}" for papel in config.tokens}


class FalhaDeOrquestracao(Exception):
    pass


@dataclass
class Evidencia:
    cenario: str
    verificacao: str
    esperado: str
    obtido: str
    sucesso: bool
    analise: str


@dataclass
class RegistroDeTentativa:
    cenario: str
    chamada: str
    correlacao: str
    tentativa: int
    destino: str
    duracao_ms: float
    status: str
    tipo_de_erro: str
    espera_s: float
    detalhar: bool


@dataclass
class Conclusao:
    cenario: str
    observacao: str
    conclusao: str


@dataclass
class Coletor:
    evidencias: list = field(default_factory=list)
    tentativas: list = field(default_factory=list)
    conclusoes: dict = field(default_factory=dict)

    def registrar(self, cenario, verificacao, esperado, obtido, analise, sucesso=None):
        if sucesso is None:
            sucesso = str(esperado) == str(obtido)
        self.evidencias.append(Evidencia(cenario, verificacao, str(esperado), str(obtido), bool(sucesso), analise))
        marca = "OK   " if sucesso else "FALHA"
        print(f"  [{marca}] {verificacao:<58} esperado={esperado!s:<20} obtido={obtido}")
        return sucesso

    def anotar(self, cenario, chamada, resultado, detalhar=True):
        for item in resultado.tentativas:
            self.tentativas.append(
                RegistroDeTentativa(
                    cenario,
                    chamada,
                    resultado.correlacao,
                    item.numero,
                    item.destino,
                    round(item.duracao_ms, 1),
                    str(item.status) if item.status is not None else "sem resposta",
                    "-" if item.categoria == "sucesso" else item.categoria,
                    round(item.espera_s, 3),
                    detalhar,
                )
            )
        return resultado

    def concluir(self, cenario, observacao, conclusao):
        self.conclusoes[cenario] = Conclusao(cenario, observacao, conclusao)

    def do_cenario(self, cenario):
        return [item for item in self.evidencias if item.cenario == cenario]

    def tentativas_do_cenario(self, cenario):
        return [item for item in self.tentativas if item.cenario == cenario]

    @property
    def total(self):
        return len(self.evidencias)

    @property
    def falhas(self):
        return [item for item in self.evidencias if not item.sucesso]


def ident(cenario, nome):
    return f"{cenario.lower()}-{nome}"


def limpar_logs():
    if config.pasta_de_logs.exists():
        shutil.rmtree(config.pasta_de_logs, ignore_errors=True)
    config.pasta_de_logs.mkdir(parents=True, exist_ok=True)


def porta_livre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tomada:
        tomada.bind(("127.0.0.1", 0))
        return tomada.getsockname()[1]


def porta_ocupada(porta, limite=0.3):
    try:
        with socket.create_connection(("127.0.0.1", porta), limite):
            return True
    except OSError:
        return False


def esperar_ate(condicao, limite=15.0, intervalo=0.05):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(intervalo)
    return False


def cabecalho_de(papel):
    return {"Authorization": f"Bearer {tokens[papel]}"}


def ler_jsonl(caminho):
    if not caminho.exists():
        return []
    eventos = []
    with caminho.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                eventos.append(json.loads(linha))
    return eventos


def percentil(valores, fracao):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    posicao = min(len(ordenados) - 1, int(round(fracao * (len(ordenados) - 1))))
    return round(ordenados[posicao], 1)


def inicio_do_evento(evento):
    concluido = datetime.fromisoformat(evento["instante"]).timestamp()
    return concluido - evento["duracao_ms"] / 1000


def pico_por_janela(eventos, janela_s=0.1):
    inicios = sorted(inicio_do_evento(evento) for evento in eventos)
    pico, esquerda = 0, 0
    for direita, instante in enumerate(inicios):
        while instante - inicios[esquerda] > janela_s:
            esquerda += 1
        pico = max(pico, direita - esquerda + 1)
    return pico


class Servidor:
    def __init__(self, identificador, porta=None, atraso_na_escrita=0.0, semente="ap5", laboratorio=True, banco=None):
        self.identificador = identificador
        self.porta = porta or porta_livre()
        self.atraso_na_escrita = atraso_na_escrita
        self.semente = semente
        self.laboratorio = laboratorio
        self.banco = banco or config.pasta_de_logs / f"{identificador}.db"
        self.caminho_do_log = config.pasta_de_logs / f"{identificador}.jsonl"
        self.caminho_da_saida = config.pasta_de_logs / f"{identificador}.saida.txt"
        self.processo = None
        self.saida = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}"

    def ambiente(self):
        ambiente = dict(os.environ)
        ambiente.update(
            {
                "BIBLIOTECA_BANCO": str(self.banco),
                "BIBLIOTECA_LOG": str(self.caminho_do_log),
                "BIBLIOTECA_PROCESSO": self.identificador,
                "BIBLIOTECA_LABORATORIO": "1" if self.laboratorio else "0",
                "BIBLIOTECA_ATRASO_NA_ESCRITA": str(self.atraso_na_escrita),
                "BIBLIOTECA_SEMENTE": self.semente,
                "PYTHONIOENCODING": "utf-8",
            }
        )
        for papel, token in tokens.items():
            ambiente[f"BIBLIOTECA_TOKEN_{papel.upper()}"] = token
        return ambiente

    def no_ar(self):
        try:
            return requests.get(f"{self.url}/v1/saude", timeout=0.5).status_code == 200
        except requests.exceptions.RequestException:
            return False

    def iniciar(self):
        config.pasta_de_logs.mkdir(parents=True, exist_ok=True)
        comando = [
            python, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(self.porta), "--log-level", "warning",
        ]
        self.saida = self.caminho_da_saida.open("a", encoding="utf-8")
        self.processo = subprocess.Popen(
            comando,
            cwd=config.raiz_do_projeto,
            env=self.ambiente(),
            stdout=self.saida,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if no_windows else 0,
        )
        if not esperar_ate(self.no_ar, limite=20):
            self.matar()
            raise FalhaDeOrquestracao(f"o servidor {self.identificador} não respondeu em 20 s")
        return self

    def fechar_saida(self):
        if self.saida is not None and not self.saida.closed:
            self.saida.close()

    def parar(self):
        if self.processo is not None and self.processo.poll() is None:
            try:
                if no_windows:
                    os.kill(self.processo.pid, signal.CTRL_BREAK_EVENT)
                else:
                    self.processo.send_signal(signal.SIGINT)
                self.processo.wait(10)
            except (OSError, subprocess.TimeoutExpired):
                self.processo.kill()
                self.processo.wait(5)
        self.processo = None
        self.fechar_saida()
        esperar_ate(lambda: not porta_ocupada(self.porta), limite=10)

    def matar(self):
        if self.processo is not None and self.processo.poll() is None:
            self.processo.kill()
            self.processo.wait(5)
        self.processo = None
        self.fechar_saida()
        esperar_ate(lambda: not porta_ocupada(self.porta), limite=10)

    def eventos(self, caminho=None, correlacao=None):
        registros = ler_jsonl(self.caminho_do_log)
        if caminho is not None:
            registros = [item for item in registros if item["caminho"] == caminho]
        if correlacao is not None:
            registros = [item for item in registros if item["correlacao"] == correlacao]
        return registros

    def esperar_eventos(self, correlacao, quantidade, limite=10.0):
        esperar_ate(lambda: len(self.eventos(correlacao=correlacao)) >= quantidade, limite=limite)
        return self.eventos(correlacao=correlacao)

    def cadastrar_livro(self, titulo, exemplares=1):
        dados = {
            "titulo": titulo,
            "autor": "Autor de Laboratório",
            "isbn": "978" + str(secrets.randbelow(10**10)).zfill(10),
            "ano": 2020,
            "exemplares_total": exemplares,
        }
        resultado = requisitar("POST", f"{self.url}/v1/livros", timeout=3.0, cabecalhos=cabecalho_de("bibliotecario"), json=dados)
        if resultado.status != 201:
            raise FalhaDeOrquestracao(f"não foi possível cadastrar o livro de teste: {resultado.status}")
        return resultado.resposta.json()

    def emprestimos_ativos(self, livro_id, leitor=None):
        itens = requests.get(f"{self.url}/v1/livros/{livro_id}/emprestimos", timeout=3.0).json()
        return [
            item for item in itens
            if item["devolvido_em"] is None and (leitor is None or item["leitor"] == leitor)
        ]

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *_):
        self.parar()
