import argparse
import json
import threading
import time
from dataclasses import dataclass, field

import requests

from medicao.estatistica import resumir
from observabilidade.contexto import cabecalho_correlacao, cabecalho_mensagem, novo_correlation_id, novo_message_id


@dataclass
class Amostra:
    indice: int
    inicio_s: float
    duracao_ms: float
    classe: str
    status: int | None
    detalhe: str
    correlation_id: str
    aquecimento: bool

    @property
    def fim_s(self):
        return self.inicio_s + self.duracao_ms / 1000


@dataclass
class ResultadoDaCarga:
    url: str
    concorrencia: int
    amostras: list
    duracao_s: float
    marcos: list = field(default_factory=list)
    abortado: bool = False
    motivo_do_aborto: str | None = None
    inicio_epoch_ms: float = 0.0

    def relativo(self, epoch_ms):
        return (epoch_ms - self.inicio_epoch_ms) / 1000

    @property
    def medidas(self):
        return [a for a in self.amostras if not a.aquecimento]

    @property
    def aquecimento(self):
        return [a for a in self.amostras if a.aquecimento]


def classificar_excecao(erro):
    if isinstance(erro, requests.exceptions.ConnectTimeout):
        return "timeout_conexao"
    if isinstance(erro, requests.exceptions.ReadTimeout):
        return "timeout_leitura"
    if isinstance(erro, requests.exceptions.ConnectionError):
        texto = repr(erro).lower()
        if "10061" in texto or "refused" in texto or "recus" in texto:
            return "conexao_recusada"
        if any(marca in texto for marca in ("10054", "10053", "reset", "aborted", "remotedisconnected", "closed")):
            return "conexao_interrompida"
        return "conexao"
    return "transporte"


def requisitar(sessao, url, timeout_s, relogio_zero, indice, aquecimento):
    correlation_id = novo_correlation_id()
    cabecalhos = {cabecalho_correlacao: correlation_id, cabecalho_mensagem: novo_message_id()}
    inicio = time.perf_counter()
    try:
        resposta = sessao.get(url, headers=cabecalhos, timeout=timeout_s)
        status = resposta.status_code
        classe = "sucesso" if status < 400 else "erro_aplicacao"
        detalhe = f"http_{status}"
    except requests.RequestException as erro:
        status = None
        classe = "erro_transporte"
        detalhe = classificar_excecao(erro)
    fim = time.perf_counter()
    return Amostra(indice, inicio - relogio_zero, (fim - inicio) * 1000, classe, status, detalhe, correlation_id, aquecimento)


def executar_carga(
    url,
    concorrencia=1,
    total=None,
    duracao_s=None,
    aquecimento=0,
    timeout_s=2.0,
    limite_de_erro=None,
    janela_de_aborto_s=1.0,
    minimo_para_abortar=10,
    eventos=(),
):
    if total is None and duracao_s is None:
        raise ValueError("informe total ou duracao_s")

    amostras = []
    marcos = []
    trava = threading.Lock()
    parar = threading.Event()
    estado = {"proximo": 0, "motivo": None}
    inicio_epoch_ms = time.time() * 1000
    relogio_zero = time.perf_counter()

    def reservar():
        with trava:
            if parar.is_set():
                return None
            if duracao_s is not None and time.perf_counter() - relogio_zero >= duracao_s:
                return None
            if total is not None and estado["proximo"] >= aquecimento + total:
                return None
            indice = estado["proximo"]
            estado["proximo"] += 1
            return indice

    def trabalhador():
        with requests.Session() as sessao:
            while (indice := reservar()) is not None:
                amostra = requisitar(sessao, url, timeout_s, relogio_zero, indice, indice < aquecimento)
                with trava:
                    amostras.append(amostra)

    def vigia():
        while not parar.wait(0.2):
            agora = time.perf_counter() - relogio_zero
            with trava:
                recentes = [a for a in amostras if a.fim_s >= agora - janela_de_aborto_s and not a.aquecimento]
            if len(recentes) < minimo_para_abortar:
                continue
            taxa = sum(1 for a in recentes if a.classe != "sucesso") / len(recentes)
            if taxa > limite_de_erro:
                estado["motivo"] = f"taxa de erro {taxa:.0%} acima de {limite_de_erro:.0%} na janela de {janela_de_aborto_s:.0f} s (t={agora:.1f} s)"
                parar.set()

    def agenda():
        for instante, rotulo, acao in sorted(eventos, key=lambda item: item[0]):
            espera = instante - (time.perf_counter() - relogio_zero)
            if espera > 0 and parar.wait(espera):
                return
            if parar.is_set():
                return
            inicio = time.perf_counter() - relogio_zero
            acao()
            marcos.append({"rotulo": rotulo, "inicio_s": round(inicio, 3), "fim_s": round(time.perf_counter() - relogio_zero, 3)})

    trabalhadores = [threading.Thread(target=trabalhador, daemon=True) for _ in range(concorrencia)]
    auxiliares = []
    if limite_de_erro is not None:
        auxiliares.append(threading.Thread(target=vigia, daemon=True))
    if eventos:
        auxiliares.append(threading.Thread(target=agenda, daemon=True))

    for linha in trabalhadores + auxiliares:
        linha.start()
    for linha in trabalhadores:
        linha.join()
    duracao = time.perf_counter() - relogio_zero
    parar.set()
    for linha in auxiliares:
        linha.join()

    amostras.sort(key=lambda a: a.indice)
    return ResultadoDaCarga(
        url, concorrencia, amostras, duracao, marcos, estado["motivo"] is not None, estado["motivo"], inicio_epoch_ms
    )


def principal():
    analisador = argparse.ArgumentParser(description="Gerador de carga em malha fechada com classificação de erros.")
    analisador.add_argument("url")
    analisador.add_argument("--concorrencia", type=int, default=1)
    analisador.add_argument("--total", type=int)
    analisador.add_argument("--duracao", type=float)
    analisador.add_argument("--aquecimento", type=int, default=0)
    analisador.add_argument("--timeout", type=float, default=2.0)
    analisador.add_argument("--slo-ms", type=float)
    argumentos = analisador.parse_args()

    resultado = executar_carga(
        argumentos.url,
        concorrencia=argumentos.concorrencia,
        total=argumentos.total if argumentos.total or argumentos.duracao else 200,
        duracao_s=argumentos.duracao,
        aquecimento=argumentos.aquecimento,
        timeout_s=argumentos.timeout,
    )
    resumo = resumir(resultado.medidas, slo_ms=argumentos.slo_ms)
    resumo["aquecimento_descartado"] = len(resultado.aquecimento)
    resumo["concorrencia"] = argumentos.concorrencia
    print(json.dumps(resumo, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    principal()
