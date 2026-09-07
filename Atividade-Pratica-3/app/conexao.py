import random
import signal
import threading
import time

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from app import config

ATRASO_MINIMO = 1
ATRASO_MAXIMO = 8
TENTATIVAS_PADRAO = 10


class BrokerIndisponivel(Exception):
    pass


def criar_cliente(identificador, *, testamento=None, keepalive=None):
    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=identificador,
        protocol=mqtt.MQTTv5,
    )
    if testamento is not None:
        topico, carga, qos, reter = testamento
        cliente.will_set(topico, carga, qos=qos, retain=reter)
    cliente.reconnect_delay_set(min_delay=ATRASO_MINIMO, max_delay=ATRASO_MAXIMO)
    cliente.keepalive = keepalive or config.KEEPALIVE_PADRAO
    return cliente


def propriedades_de_sessao(expiracao):
    propriedades = Properties(PacketTypes.CONNECT)
    propriedades.SessionExpiryInterval = expiracao
    return propriedades


def espera_com_jitter(tentativa):
    teto = min(ATRASO_MAXIMO, ATRASO_MINIMO * (2 ** (tentativa - 1)))
    return round(random.uniform(teto / 2, teto), 2)


def conectar(
    cliente,
    *,
    host=None,
    porta=None,
    keepalive=None,
    sessao_persistente=False,
    expiracao=config.EXPIRACAO_DA_SESSAO,
    tentativas=TENTATIVAS_PADRAO,
    registrador=None,
):
    host = host or config.BROKER_HOST
    porta = porta or config.BROKER_PORTA
    keepalive = keepalive or cliente.keepalive or config.KEEPALIVE_PADRAO
    propriedades = propriedades_de_sessao(expiracao) if sessao_persistente else None
    clean_start = False if sessao_persistente else True

    ultima_falha = None
    for tentativa in range(1, tentativas + 1):
        try:
            cliente.connect(
                host,
                porta,
                keepalive,
                clean_start=clean_start,
                properties=propriedades,
            )
            return
        except OSError as erro:
            ultima_falha = erro
            if tentativa == tentativas:
                break
            espera = espera_com_jitter(tentativa)
            if registrador is not None:
                registrador.evento(
                    "conexao-falhou",
                    tentativa=tentativa,
                    espera_s=espera,
                    detalhe=str(erro),
                )
            time.sleep(espera)

    raise BrokerIndisponivel(
        f"não foi possível conectar em {host}:{porta} após {tentativas} tentativas: {ultima_falha}"
    )


class Encerramento:
    def __init__(self):
        self.solicitado = threading.Event()
        for nome in ("SIGINT", "SIGTERM", "SIGBREAK"):
            recebido = getattr(signal, nome, None)
            if recebido is not None:
                try:
                    signal.signal(recebido, self._atender)
                except (ValueError, OSError):
                    pass

    def _atender(self, numero, quadro):
        self.solicitado.set()

    def aguardar(self, limite=None):
        return self.solicitado.wait(limite)

    def aguardar_com_alvo(self, alvo=None, limite=None, intervalo=0.1):
        fim = None if not limite else time.monotonic() + limite
        while True:
            if self.solicitado.is_set():
                return "encerramento"
            if alvo is not None and alvo.is_set():
                return "alvo"
            if fim is not None and time.monotonic() >= fim:
                return "limite"
            time.sleep(intervalo)

    def __bool__(self):
        return self.solicitado.is_set()
