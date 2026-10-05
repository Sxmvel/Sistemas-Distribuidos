import random
import time
import uuid
from dataclasses import dataclass, field

import requests

categorias_transitorias = {
    "timeout-de-leitura",
    "timeout-de-conexao",
    "conexao-recusada",
    "conexao-interrompida",
}
status_transitorios = {502, 503, 504}


@dataclass
class Tentativa:
    numero: int
    destino: str
    duracao_ms: float
    status: int | None
    categoria: str
    espera_s: float = 0.0

    @property
    def transitoria(self):
        return self.categoria in categorias_transitorias or self.status in status_transitorios


@dataclass
class Resultado:
    correlacao: str
    tentativas: list = field(default_factory=list)
    resposta: requests.Response | None = None
    erro: Exception | None = None

    @property
    def ok(self):
        return self.resposta is not None and self.resposta.ok

    @property
    def ultima(self):
        return self.tentativas[-1]

    @property
    def categoria(self):
        return self.ultima.categoria

    @property
    def status(self):
        return self.ultima.status

    @property
    def duracao_total_ms(self):
        return sum(item.duracao_ms + item.espera_s * 1000 for item in self.tentativas)


def classificar_excecao(erro):
    if isinstance(erro, requests.exceptions.ConnectTimeout):
        return "timeout-de-conexao"
    if isinstance(erro, requests.exceptions.ReadTimeout):
        return "timeout-de-leitura"
    if isinstance(erro, requests.exceptions.ConnectionError):
        texto = str(erro).lower()
        if "10061" in texto or "refused" in texto or "recusou" in texto:
            return "conexao-recusada"
        return "conexao-interrompida"
    return type(erro).__name__


def classificar_status(status):
    if status >= 500:
        return "erro-de-aplicacao"
    if status >= 400:
        return "erro-do-cliente"
    return "sucesso"


def executar_tentativa(metodo, url, numero, timeout, correlacao, cabecalhos=None, **kwargs):
    enviados = dict(cabecalhos or {})
    enviados["X-Request-ID"] = correlacao
    enviados["X-Tentativa"] = str(numero)
    inicio = time.perf_counter()
    try:
        resposta = requests.request(metodo, url, timeout=timeout, headers=enviados, **kwargs)
    except requests.exceptions.RequestException as erro:
        duracao = (time.perf_counter() - inicio) * 1000
        return Tentativa(numero, url, duracao, None, classificar_excecao(erro)), None, erro
    duracao = (time.perf_counter() - inicio) * 1000
    tentativa = Tentativa(numero, url, duracao, resposta.status_code, classificar_status(resposta.status_code))
    return tentativa, resposta, None


def calcular_espera(indice, base=0.2, jitter=0.1, teto=5.0, sortear=random.uniform):
    return min(teto, base * (2**indice)) + sortear(0, jitter)


def requisitar(metodo, url, timeout=0.5, cabecalhos=None, correlacao=None, **kwargs):
    correlacao = correlacao or uuid.uuid4().hex[:12]
    tentativa, resposta, erro = executar_tentativa(metodo, url, 1, timeout, correlacao, cabecalhos, **kwargs)
    return Resultado(correlacao, [tentativa], resposta, erro)


def chamar_com_retry(
    metodo,
    url,
    tentativas=4,
    timeout=0.5,
    base=0.2,
    jitter=0.1,
    teto=5.0,
    cabecalhos=None,
    correlacao=None,
    ao_falhar=None,
    dormir=time.sleep,
    sortear=random.uniform,
    **kwargs,
):
    resultado = Resultado(correlacao or uuid.uuid4().hex[:12])
    for numero in range(1, tentativas + 1):
        tentativa, resposta, erro = executar_tentativa(
            metodo, url, numero, timeout, resultado.correlacao, cabecalhos, **kwargs
        )
        resultado.tentativas.append(tentativa)
        resultado.resposta, resultado.erro = resposta, erro
        if not tentativa.transitoria or numero == tentativas:
            return resultado
        tentativa.espera_s = calcular_espera(numero - 1, base, jitter, teto, sortear)
        if ao_falhar is not None:
            ao_falhar(tentativa)
        dormir(tentativa.espera_s)
    return resultado


def chamar_com_failover(
    metodo,
    caminho,
    enderecos,
    rodadas=2,
    timeout=0.5,
    base=0.2,
    jitter=0.1,
    cabecalhos=None,
    correlacao=None,
    dormir=time.sleep,
    sortear=random.uniform,
    **kwargs,
):
    resultado = Resultado(correlacao or uuid.uuid4().hex[:12])
    numero = 0
    for rodada in range(rodadas):
        for endereco in enderecos:
            numero += 1
            tentativa, resposta, erro = executar_tentativa(
                metodo, f"{endereco}{caminho}", numero, timeout, resultado.correlacao, cabecalhos, **kwargs
            )
            resultado.tentativas.append(tentativa)
            resultado.resposta, resultado.erro = resposta, erro
            if not tentativa.transitoria:
                return resultado
        if rodada < rodadas - 1:
            resultado.ultima.espera_s = calcular_espera(rodada, base, jitter, sortear=sortear)
            dormir(resultado.ultima.espera_s)
    return resultado


def imprimir_falha(tentativa):
    print(f"falha {tentativa.categoria}; retry em {tentativa.espera_s:.2f}s")


def get_com_retry(url, tentativas=4, timeout=0.5):
    resultado = chamar_com_retry("GET", url, tentativas=tentativas, timeout=timeout, ao_falhar=imprimir_falha)
    if resultado.erro is not None:
        raise resultado.erro
    resultado.resposta.raise_for_status()
    return resultado.resposta.json()


class Disjuntor:
    def __init__(self, limite_de_falhas=3, tempo_aberto=1.5, relogio=time.monotonic):
        self.limite_de_falhas = limite_de_falhas
        self.tempo_aberto = tempo_aberto
        self.relogio = relogio
        self.estado = "fechado"
        self.falhas_seguidas = 0
        self.aberto_desde = None
        self.historico = []

    def mudar(self, estado):
        if estado != self.estado:
            self.historico.append((self.estado, estado))
            self.estado = estado

    def permite(self):
        if self.estado == "aberto" and self.relogio() - self.aberto_desde >= self.tempo_aberto:
            self.mudar("meio-aberto")
        return self.estado != "aberto"

    def registrar_sucesso(self):
        self.falhas_seguidas = 0
        self.mudar("fechado")

    def registrar_falha(self):
        self.falhas_seguidas += 1
        if self.estado == "meio-aberto" or self.falhas_seguidas >= self.limite_de_falhas:
            self.aberto_desde = self.relogio()
            self.mudar("aberto")

    def chamar(self, metodo, url, timeout=0.5, cabecalhos=None, **kwargs):
        correlacao = uuid.uuid4().hex[:12]
        if not self.permite():
            return Resultado(correlacao, [Tentativa(1, url, 0.0, None, "circuito-aberto")])
        resultado = requisitar(metodo, url, timeout, cabecalhos, correlacao, **kwargs)
        if resultado.ultima.transitoria:
            self.registrar_falha()
        else:
            self.registrar_sucesso()
        return resultado
