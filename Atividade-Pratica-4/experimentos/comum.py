import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field

from app import config
from app.registro import ler_log

PYTHON = sys.executable
RAIZ = config.RAIZ_DO_PROJETO
NO_WINDOWS = os.name == "nt"

MODULO_DO_SERVIDOR = "app.servidor"


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
class Medicao:
    cenario: str
    chamada: str
    deadline: str
    status: str
    latencia_ms: float
    observacao: str


@dataclass
class Coletor:
    evidencias: list = field(default_factory=list)
    medicoes: list = field(default_factory=list)

    def registrar(self, cenario, verificacao, esperado, obtido, analise, sucesso=None):
        if sucesso is None:
            sucesso = str(esperado) == str(obtido)
        self.evidencias.append(
            Evidencia(cenario, verificacao, str(esperado), str(obtido), bool(sucesso), analise)
        )
        marca = "OK   " if sucesso else "FALHA"
        print(f"  [{marca}] {verificacao:<54} esperado={esperado!s:<24} obtido={obtido}")
        return sucesso

    def medir(self, cenario, chamada, deadline, resultado, observacao=""):
        self.medicoes.append(
            Medicao(
                cenario,
                chamada,
                "sem deadline" if deadline is None else f"{deadline:g} s",
                resultado.status,
                round(resultado.latencia_ms, 1),
                observacao,
            )
        )
        return resultado

    def anotar_medicao(self, cenario, chamada, deadline, status, latencia_ms, observacao=""):
        self.medicoes.append(
            Medicao(
                cenario,
                chamada,
                "sem deadline" if deadline is None else f"{deadline:g} s",
                status,
                round(latencia_ms, 1),
                observacao,
            )
        )

    def do_cenario(self, cenario):
        return [item for item in self.evidencias if item.cenario == cenario]

    def medicoes_do_cenario(self, cenario):
        return [item for item in self.medicoes if item.cenario == cenario]

    @property
    def total(self):
        return len(self.evidencias)

    @property
    def falhas(self):
        return [item for item in self.evidencias if not item.sucesso]


def ident(cenario, nome):
    return f"{cenario}-{nome}"


def porta_livre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tomada:
        tomada.bind(("127.0.0.1", 0))
        return tomada.getsockname()[1]


def porta_ocupada(porta, limite=0.4):
    try:
        with socket.create_connection(("127.0.0.1", porta), limite):
            return True
    except OSError:
        return False


def esperar_porta(porta, ocupada=True, limite=25.0):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if porta_ocupada(porta) == ocupada:
            return True
        time.sleep(0.1)
    estado = "aberta" if ocupada else "fechada"
    raise FalhaDeOrquestracao(f"a porta {porta} não ficou {estado} em {limite:g}s")


def esperar_ate(condicao, limite=20.0, intervalo=0.1):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(intervalo)
    return False


def iniciar_processo(modulo, *argumentos, identificador=None):
    comando = [PYTHON, "-m", modulo, *[str(item) for item in argumentos]]
    if "--silencioso" not in comando:
        comando.append("--silencioso")
    config.PASTA_DE_LOGS.mkdir(parents=True, exist_ok=True)
    nome = identificador or modulo.rsplit(".", 1)[-1]
    saida = (config.PASTA_DE_LOGS / f"{nome}.saida.txt").open("w", encoding="utf-8")
    criacao = subprocess.CREATE_NEW_PROCESS_GROUP if NO_WINDOWS else 0
    processo = subprocess.Popen(
        comando,
        cwd=RAIZ,
        stdout=saida,
        stderr=subprocess.STDOUT,
        creationflags=criacao,
    )
    processo._saida = saida
    return processo


def _fechar_saida(processo):
    saida = getattr(processo, "_saida", None)
    if saida is not None and not saida.closed:
        saida.close()


def encerrar_processo(processo, limite=12.0):
    if processo.poll() is not None:
        _fechar_saida(processo)
        return processo.returncode
    try:
        if NO_WINDOWS:
            os.kill(processo.pid, signal.CTRL_BREAK_EVENT)
        else:
            processo.send_signal(signal.SIGINT)
    except OSError:
        processo.terminate()
    try:
        processo.wait(limite)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(5)
    finally:
        _fechar_saida(processo)
    return processo.returncode


def matar_processo(processo):
    if processo.poll() is None:
        processo.kill()
        processo.wait(10)
    _fechar_saida(processo)
    return processo.returncode


def esperar_processo(processo, limite=60.0):
    try:
        processo.wait(limite)
    except subprocess.TimeoutExpired:
        matar_processo(processo)
        raise FalhaDeOrquestracao(f"processo {processo.pid} não terminou em {limite:g}s")
    _fechar_saida(processo)
    return processo.returncode


class Servidor:
    def __init__(
        self,
        identificador,
        porta=None,
        workers=config.WORKERS_PADRAO,
        semear=0,
        custo_por_codigo=config.CUSTO_POR_CODIGO_NA_MULTA,
        atraso_na_escrita=0.0,
    ):
        self.identificador = identificador
        self.porta = porta or porta_livre()
        self.workers = workers
        self.semear = semear
        self.custo_por_codigo = custo_por_codigo
        self.atraso_na_escrita = atraso_na_escrita
        self.processo = None

    @property
    def endereco(self):
        return f"127.0.0.1:{self.porta}"

    def iniciar(self):
        self.processo = iniciar_processo(
            MODULO_DO_SERVIDOR,
            "--porta",
            self.porta,
            "--workers",
            self.workers,
            "--id",
            self.identificador,
            "--semear",
            self.semear,
            "--custo-por-codigo",
            self.custo_por_codigo,
            "--atraso-na-escrita",
            self.atraso_na_escrita,
            identificador=self.identificador,
        )
        esperar_porta(self.porta, ocupada=True)
        return self

    def parar(self):
        if self.processo is not None:
            encerrar_processo(self.processo)
            self.processo = None
        esperar_porta(self.porta, ocupada=False, limite=15)

    def matar(self):
        if self.processo is not None:
            matar_processo(self.processo)
            self.processo = None
        esperar_porta(self.porta, ocupada=False, limite=15)

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *_):
        if self.processo is not None:
            try:
                self.parar()
            except FalhaDeOrquestracao:
                self.matar()


def eventos(identificador, *acoes):
    registros = ler_log(identificador)
    if not acoes:
        return registros
    return [evento for evento in registros if evento["acao"] in acoes]


def chamadas_concluidas(identificador, metodo=None, status=None):
    registros = eventos(identificador, "chamada-concluida")
    if metodo is not None:
        registros = [item for item in registros if item.get("metodo") == metodo]
    if status is not None:
        registros = [item for item in registros if item.get("status") == status]
    return registros


def percentil(valores, fracao):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    posicao = min(len(ordenados) - 1, int(round(fracao * (len(ordenados) - 1))))
    return round(ordenados[posicao], 1)
