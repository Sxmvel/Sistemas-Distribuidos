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
SERVICO_DO_BROKER = "mosquitto"
NO_WINDOWS = os.name == "nt"

ACOES_DE_PUBLICACAO = ("publicado", "reenviado")
ACOES_DE_RECEBIMENTO = ("recebido", "aplicado", "duplicado-descartado", "status-aplicado")


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
class Coletor:
    evidencias: list = field(default_factory=list)

    def registrar(self, cenario, verificacao, esperado, obtido, analise, sucesso=None):
        if sucesso is None:
            sucesso = str(esperado) == str(obtido)
        self.evidencias.append(
            Evidencia(cenario, verificacao, str(esperado), str(obtido), bool(sucesso), analise)
        )
        marca = "OK   " if sucesso else "FALHA"
        print(f"  [{marca}] {verificacao:<52} esperado={esperado!s:<22} obtido={obtido}")
        return sucesso

    def do_cenario(self, cenario):
        return [evidencia for evidencia in self.evidencias if evidencia.cenario == cenario]

    @property
    def total(self):
        return len(self.evidencias)

    @property
    def falhas(self):
        return [evidencia for evidencia in self.evidencias if not evidencia.sucesso]


def ident(cenario, nome):
    return f"{cenario}-{nome}"


def executar_compose(*argumentos, checar=True):
    processo = subprocess.run(
        ["docker", "compose", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    if checar and processo.returncode != 0:
        raise FalhaDeOrquestracao(
            f"docker compose {' '.join(argumentos)} falhou: {processo.stderr.strip()}"
        )
    return processo


def docker_disponivel():
    try:
        processo = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return processo.returncode == 0


def broker_no_ar(limite=1.0):
    try:
        with socket.create_connection((config.BROKER_HOST, config.BROKER_PORTA), limite):
            return True
    except OSError:
        return False


def esperar_broker(no_ar=True, limite=45.0):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if broker_no_ar(0.5) == no_ar:
            return True
        time.sleep(0.3)
    estado = "no ar" if no_ar else "fora do ar"
    raise FalhaDeOrquestracao(f"o broker não ficou {estado} em {limite}s")


def subir_broker():
    executar_compose("up", "-d", SERVICO_DO_BROKER)
    esperar_broker(no_ar=True)


def parar_broker():
    executar_compose("stop", "-t", "2", SERVICO_DO_BROKER)
    esperar_broker(no_ar=False, limite=30)


def iniciar_broker():
    executar_compose("start", SERVICO_DO_BROKER)
    esperar_broker(no_ar=True)


def derrubar_broker():
    executar_compose("down", "-v", checar=False)


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


def encerrar_processo(processo, limite=15.0):
    if processo.poll() is not None:
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


def _fechar_saida(processo):
    saida = getattr(processo, "_saida", None)
    if saida is not None and not saida.closed:
        saida.close()


def esperar_processo(processo, limite=60.0):
    try:
        processo.wait(limite)
    except subprocess.TimeoutExpired:
        matar_processo(processo)
        raise FalhaDeOrquestracao(f"processo {processo.pid} não terminou em {limite}s")
    _fechar_saida(processo)
    return processo.returncode


def esperar_ate(condicao, limite=30.0, intervalo=0.2):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(intervalo)
    return False


def esperar_conexao(identificador, limite=30.0):
    if not esperar_ate(
        lambda: any(evento["acao"] == "conectado" for evento in ler_log(identificador)),
        limite,
    ):
        raise FalhaDeOrquestracao(f"{identificador} não conectou em {limite}s")


def eventos(identificador, *acoes):
    registros = ler_log(identificador)
    if not acoes:
        return registros
    return [evento for evento in registros if evento["acao"] in acoes]


def publicadas(identificador, aceitas_apenas=True):
    registros = eventos(identificador, *ACOES_DE_PUBLICACAO)
    if aceitas_apenas:
        registros = [evento for evento in registros if evento.get("aceito")]
    return registros


def confirmadas(identificador):
    return [evento for evento in publicadas(identificador) if evento.get("confirmado")]


def recebidas(identificador, tipos=None):
    registros = eventos(identificador, "recebido", "aplicado", "duplicado-descartado")
    if tipos is not None:
        registros = [evento for evento in registros if evento.get("tipo") in tipos]
    return registros


def status_recebidos(identificador):
    registros = eventos(identificador, "recebido", "status-aplicado")
    return [
        evento
        for evento in registros
        if evento.get("tipo") == "status" or evento["acao"] == "status-aplicado"
    ]


def resumo_de(identificador):
    encontrados = eventos(identificador, "resumo")
    return encontrados[-1] if encontrados else {}


def chaves_de_mensagem(registros):
    return {
        (evento.get("producer_id") or evento.get("processo"), evento.get("sequence"))
        for evento in registros
        if evento.get("sequence") is not None
    }


def sequencias_publicadas(identificador):
    return {
        (evento["processo"], evento["sequence"])
        for evento in publicadas(identificador)
        if evento.get("sequence") is not None
    }


def titulo_do_cenario(modulo):
    return f"{modulo.CODIGO} — {modulo.TITULO}"


def limpar_estado_do_broker():
    executar_compose("down", checar=False)
    dados = RAIZ / "mosquitto" / "data"
    if dados.exists():
        for arquivo in dados.glob("*.db"):
            try:
                arquivo.unlink()
            except OSError:
                pass


def versao_do_broker():
    processo = subprocess.run(
        ["docker", "compose", "run", "--rm", "--entrypoint", "mosquitto", SERVICO_DO_BROKER, "-h"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    primeira = (processo.stdout or processo.stderr).strip().splitlines()
    return primeira[0] if primeira else "desconhecida"


def preparar_ambiente():
    if not docker_disponivel():
        raise FalhaDeOrquestracao(
            "o daemon do Docker não respondeu. Abra o Docker Desktop e tente novamente."
        )
    limpar_estado_do_broker()
    subir_broker()


def garantir_broker():
    if not broker_no_ar(1.0):
        iniciar_broker()
