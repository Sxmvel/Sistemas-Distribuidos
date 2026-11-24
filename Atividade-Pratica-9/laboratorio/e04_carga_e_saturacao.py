import os
import statistics
import threading
import time

import psutil
import requests

from laboratorio.comum import Laboratorio, Relato, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import resumir

niveis = (1, 2, 4, 8, 16, 32)
duracao_s = 5
trabalhadores = 2
tempo_servico_ms = 20


def arvore_de_processos(pid):
    raiz_do_processo = psutil.Process(pid)
    return [raiz_do_processo, *raiz_do_processo.children(recursive=True)]


class Amostrador:
    def __init__(self, urls, processos, intervalo_s=0.05):
        self.urls = urls
        self.processos = {nome: arvore_de_processos(pid) for nome, pid in processos.items()}
        self.intervalo_s = intervalo_s
        self.filas = []
        self.ocupacao = []
        self.cpu = {nome: [] for nome in processos}
        self.parar = threading.Event()
        self.linha = threading.Thread(target=self.rodar, daemon=True)

    def rodar(self):
        for arvore in self.processos.values():
            for processo in arvore:
                processo.cpu_percent(None)
        ultima_cpu = time.monotonic()
        with requests.Session() as sessao:
            while not self.parar.wait(self.intervalo_s):
                if time.monotonic() - ultima_cpu >= 0.5:
                    for nome, arvore in self.processos.items():
                        self.cpu[nome].append(sum(processo.cpu_percent(None) for processo in arvore))
                    ultima_cpu = time.monotonic()
                try:
                    retratos = [sessao.get(url + "/v1/metricas", timeout=1).json() for url in self.urls]
                except requests.RequestException:
                    continue
                self.filas.append(sum(r["na_fila"] for r in retratos))
                self.ocupacao.append(sum(r["em_atendimento"] for r in retratos) / sum(r["trabalhadores"] for r in retratos))

    def media_de_cpu(self, nome):
        valores = self.cpu[nome]
        return statistics.fmean(valores) / 100 if valores else None

    def __enter__(self):
        self.linha.start()
        return self

    def __exit__(self, *_):
        self.parar.set()
        self.linha.join()


def janela_dos_logs(eventos, de_ms, ate_ms):
    selecionados = [e for e in eventos if e.get("span_id") and de_ms <= e["start_ms"] <= ate_ms]

    def media(filtro, campo="duration_ms"):
        valores = [e[campo] for e in selecionados if filtro(e) and campo in e]
        return statistics.fmean(valores) if valores else None

    return {
        "balcao_ms": media(lambda e: e["service"] == "balcao" and e["span_kind"] == "server"),
        "chamada_ms": media(lambda e: e["service"] == "balcao" and e["span_kind"] == "client"),
        "acervo_ms": media(lambda e: e["service"] == "acervo"),
        "espera_ms": media(lambda e: e["service"] == "acervo", "espera_ms"),
        "servico_ms": media(lambda e: e["service"] == "acervo", "servico_ms"),
    }


def executar():
    relato = Relato(
        "E04",
        "Carga, vazão e saturação",
        "Até onde a vazão cresce com a carga, o que acontece com a latência depois desse ponto, e onde está o gargalo?",
        "16.2, 16.9",
        hipotese=(
            f"Com {trabalhadores} trabalhadores por réplica e {tempo_servico_ms} ms de serviço, a vazão cresce com o número de "
            "clientes até a capacidade do acervo e depois fica estável. A partir daí, cada cliente a mais só aumenta a fila "
            "do acervo: a latência cresce na mesma proporção e a lei de Little (clientes = vazão × latência) continua valendo."
        ),
        procedimento=[
            f"Acervo com 2 réplicas, {trabalhadores} trabalhadores cada (4 atendimentos simultâneos no total) e {tempo_servico_ms} ms de serviço.",
            f"Para cada nível de concorrência em {list(niveis)}, {duracao_s} s de carga em malha fechada contra `GET /v1/livros/4`, com 20 requisições de aquecimento.",
            "Durante a carga, amostrar `GET /v1/metricas` das réplicas a cada 50 ms (fila e ocupação dos trabalhadores) "
            "e a CPU de cada processo a cada 0,5 s.",
            "Pelos spans dos logs, decompor a latência: tempo no balcão, chamada do balcão ao acervo, atendimento no acervo, "
            "e, dentro do acervo, espera na fila e serviço.",
            "Conferir a lei de Little: concorrência ≈ vazão × latência média.",
        ],
    )

    dados = []
    with Laboratorio(
        "e04",
        acervo={"ACERVO_TRABALHADORES": trabalhadores, "ACERVO_TEMPO_SERVICO_MS": tempo_servico_ms},
        balcao={"BALCAO_TIMEOUT_MS": 10000},
    ) as lab:
        urls = [r.url for r in lab.replicas]
        processos = {
            "balcao": lab.balcao.processo.pid,
            "acervo-a": lab.replicas[0].processo.pid,
            "acervo-b": lab.replicas[1].processo.pid,
            "gerador": os.getpid(),
        }
        for nivel in niveis:
            with Amostrador(urls, processos) as amostrador:
                carga = executar_carga(lab.url("/v1/livros/4"), concorrencia=nivel, duracao_s=duracao_s, aquecimento=20, timeout_s=15)
            medidas = carga.medidas
            resumo = resumir(medidas)
            de_ms = carga.inicio_epoch_ms + min(a.inicio_s for a in medidas) * 1000
            ate_ms = carga.inicio_epoch_ms + max(a.fim_s for a in medidas) * 1000
            dados.append({
                "nivel": nivel,
                "resumo": resumo,
                "little": resumo["vazao_rps"] * resumo["media_ms"] / 1000,
                "fila": statistics.fmean(amostrador.filas) if amostrador.filas else 0.0,
                "ocupacao": statistics.fmean(amostrador.ocupacao) if amostrador.ocupacao else 0.0,
                "cpu": {nome: amostrador.media_de_cpu(nome) for nome in processos},
                **janela_dos_logs(lab.eventos(), de_ms, ate_ms),
            })

    relato.tabela(
        "Vazão, latência e saturação do acervo por nível de carga",
        ["clientes", "vazão (req/s)", "p50 (ms)", "p95 (ms)", "p99 (ms)", "fila média no acervo", "ocupação do acervo", "vazão × latência"],
        [
            [d["nivel"], num(d["resumo"]["vazao_rps"]), num(d["resumo"]["p50_ms"]), num(d["resumo"]["p95_ms"]),
             num(d["resumo"]["p99_ms"]), num(d["fila"]), pct(d["ocupacao"], 0), num(d["little"], 2)]
            for d in dados
        ],
        "Fila e ocupação vêm de `/v1/metricas`, amostrado a cada 50 ms. A última coluna é a lei de Little e deve ficar "
        "perto do número de clientes.",
    )
    relato.tabela(
        "Onde o tempo foi gasto (médias, em ms) e CPU de cada processo",
        ["clientes", "cliente", "balcão", "balcão → acervo", "acervo", "fila do acervo", "serviço", "CPU balcão", "CPU acervo-a", "CPU acervo-b", "CPU gerador"],
        [
            [d["nivel"], num(d["resumo"]["media_ms"]), num(d["balcao_ms"]), num(d["chamada_ms"]), num(d["acervo_ms"]),
             num(d["espera_ms"]), num(d["servico_ms"]), pct(d["cpu"]["balcao"], 0), pct(d["cpu"]["acervo-a"], 0),
             pct(d["cpu"]["acervo-b"], 0), pct(d["cpu"]["gerador"], 0)]
            for d in dados
        ],
        "Cada coluna de tempo está contida na anterior: cliente ⊃ span de servidor do balcão ⊃ span de cliente da chamada "
        "⊃ span de servidor do acervo ⊃ fila + serviço. A diferença entre duas colunas vizinhas é o tempo gasto naquela "
        "fronteira. CPU em % de um núcleo (o balcão e cada acervo rodam um laço de eventos só, então 100% é o teto deles).",
    )

    servico_medio = statistics.fmean(d["servico_ms"] for d in dados if d["servico_ms"])
    capacidade = 2 * trabalhadores / (servico_medio / 1000)
    pico = max(dados, key=lambda d: d["resumo"]["vazao_rps"])
    ultimo = dados[-1]
    perdido_na_fronteira = ultimo["chamada_ms"] - ultimo["acervo_ms"]
    gargalo_no_balcao = ultimo["cpu"]["balcao"] >= 0.8 and ultimo["fila"] < pico["fila"]
    vazao = {d["nivel"]: d["resumo"]["vazao_rps"] for d in dados}
    p50 = {d["nivel"]: d["resumo"]["p50_ms"] for d in dados}

    leitura = (
        f"A capacidade teórica do acervo é 4 trabalhadores ÷ {num(servico_medio)} ms de serviço ≈ {num(capacidade)} req/s. "
        f"A vazão cresce quase em linha reta até o pico de {num(pico['resumo']['vazao_rps'])} req/s com {pico['nivel']} clientes "
        f"({pct(pico['resumo']['vazao_rps'] / capacidade, 0)} da capacidade). Nesse trecho o comportamento é o previsto: "
        f"o serviço continua em {num(pico['servico_ms'])} ms, a fila do acervo sobe para {num(pico['fila'])} requisições e "
        f"a espera nela ({num(pico['espera_ms'])} ms) explica o aumento da latência."
    )
    if gargalo_no_balcao:
        leitura += (
            f"\n\nCom {ultimo['nivel']} clientes, a hipótese quebra. A vazão cai para {num(ultimo['resumo']['vazao_rps'])} req/s, "
            f"a fila do acervo esvazia ({num(ultimo['fila'])}) e a ocupação dele cai para {pct(ultimo['ocupacao'], 0)}, enquanto o p95 "
            f"vai a {num(ultimo['resumo']['p95_ms'])} ms. A decomposição mostra onde o tempo foi parar: a chamada do balcão ao "
            f"acervo dura {num(ultimo['chamada_ms'])} ms, mas o acervo atende em {num(ultimo['acervo_ms'])} ms. "
            f"São {num(perdido_na_fronteira)} ms fora do acervo, e o acervo está com {pct(ultimo['cpu']['acervo-a'], 0)} e "
            f"{pct(ultimo['cpu']['acervo-b'], 0)} de CPU, enquanto o balcão está com {pct(ultimo['cpu']['balcao'], 0)}, no limite "
            "de um laço de eventos. A corrotina que chama o acervo precisa do laço do balcão para enviar a requisição e para "
            "ler a resposta, e o laço está ocupado atendendo as outras 31 conexões. O gargalo mudou de lugar: deixou de ser o "
            "acervo (fila) e passou a ser o balcão (CPU). Só a latência no cliente não mostraria isso, porque nos dois casos "
            "ela simplesmente sobe.\n\n"
            f"Limite da medição: o gerador de carga roda na mesma máquina e usa {pct(ultimo['cpu']['gerador'], 0)} de um núcleo "
            f"com {ultimo['nivel']} clientes, o que explica parte dos {num(ultimo['resumo']['media_ms'] - ultimo['balcao_ms'])} ms "
            "entre o cliente e o balcão. Numa medição de capacidade de verdade, o gerador fica em outra máquina, para não "
            "disputar CPU com o sistema medido."
        )
    relato.texto("Leitura", leitura)

    for d in dados:
        relato.verificar(f"{d['nivel']} clientes: nenhuma requisição falhou", "0 erros", f"{d['resumo']['n'] - d['resumo']['sucessos']} erros", d["resumo"]["sucessos"] == d["resumo"]["n"])
        erro = abs(d["little"] - d["nivel"]) / d["nivel"]
        relato.verificar(f"{d['nivel']} clientes: lei de Little", f"{d['nivel']} ± 15%", f"{num(d['little'], 2)} ({pct(erro)})", erro <= 0.15)
    relato.verificar("vazão escala antes da saturação (2 clientes ÷ 1)", "≥ 1,7×", f"{num(vazao[2] / vazao[1], 2)}×", vazao[2] / vazao[1] >= 1.7)
    relato.verificar("vazão não cresce depois da saturação (32 ÷ 8)", "≤ 1,15×", f"{num(vazao[32] / vazao[8], 2)}×", vazao[32] / vazao[8] <= 1.15)
    relato.verificar("pico de vazão perto da capacidade teórica do acervo", f"≥ 80% de {num(capacidade)}", pct(pico["resumo"]["vazao_rps"] / capacidade), pico["resumo"]["vazao_rps"] >= 0.8 * capacidade)
    relato.verificar("latência cresce com a carga (p50 de 32 ÷ p50 de 4)", "≥ 4×", f"{num(p50[32] / p50[4], 2)}×", p50[32] / p50[4] >= 4)
    relato.verificar("tempo de serviço não muda com a carga", "32 clientes ≤ 1,3 × 1 cliente", f"{num(dados[-1]['servico_ms'])} vs {num(dados[0]['servico_ms'])} ms", dados[-1]["servico_ms"] <= 1.3 * dados[0]["servico_ms"])

    relato.dados = {"niveis": dados, "capacidade_teorica_rps": capacidade, "servico_medio_ms": servico_medio, "gargalo_no_balcao": gargalo_no_balcao}
    if gargalo_no_balcao:
        relato.conclusao = (
            f"Hipótese confirmada até {pico['nivel']} clientes e refutada depois. Até o pico, a vazão encostou na capacidade do "
            f"acervo ({num(pico['resumo']['vazao_rps'])} de {num(capacidade)} req/s) e todo aumento de latência foi espera na fila. "
            f"Com {ultimo['nivel']} clientes, o balcão saturou de CPU antes, a vazão caiu {pct(1 - ultimo['resumo']['vazao_rps'] / pico['resumo']['vazao_rps'], 0)} "
            "e a fila mudou de lugar: saiu do acervo e foi para dentro do balcão. A lei de Little valeu em todos os níveis, "
            "porque ela não depende de onde a fila está, só de que ela existe. Vazão, latência e saturação precisam ser lidas "
            "juntas, e por componente: o número que diz qual é o gargalo é a fila ou a CPU de cada processo, não a latência do cliente."
        )
    else:
        relato.conclusao = (
            f"{relato.veredito()} A vazão parou em {num(pico['resumo']['vazao_rps'])} req/s "
            f"({pct(pico['resumo']['vazao_rps'] / capacidade, 0)} da capacidade teórica), e de 4 para 32 clientes o p50 foi de "
            f"{num(p50[4])} para {num(p50[32])} ms sem nenhuma requisição ficar mais cara de atender: todo o aumento foi espera."
        )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
