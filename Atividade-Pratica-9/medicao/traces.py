import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


def ler_eventos(*caminhos):
    eventos = []
    for caminho in caminhos:
        caminho = Path(caminho)
        if not caminho.exists():
            continue
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                eventos.append(json.loads(linha))
    return eventos


def spans(eventos):
    return [e for e in eventos if e.get("span_id")]


def agrupar_por_correlacao(eventos):
    grupos = defaultdict(list)
    for evento in spans(eventos):
        grupos[evento["correlation_id"]].append(evento)
    return dict(grupos)


@dataclass
class No:
    evento: dict
    filhos: list = field(default_factory=list)


def montar_arvore(spans_da_operacao):
    nos = {s["span_id"]: No(s) for s in spans_da_operacao}
    raizes = []
    for no in nos.values():
        pai = no.evento.get("parent_span_id")
        if pai in nos:
            nos[pai].filhos.append(no)
        else:
            raizes.append(no)
    for no in nos.values():
        no.filhos.sort(key=lambda filho: filho.evento["start_ms"])
    raizes.sort(key=lambda raiz: raiz.evento["start_ms"])
    return raizes


def descrever(evento):
    partes = [f"{evento['service']}/{evento['instance']}", evento["span_kind"], evento["operation"]]
    if evento.get("attempt"):
        partes.append(f"tentativa {evento['attempt']}")
    if evento.get("replica"):
        partes.append(f"-> {evento['replica'].rsplit(':', 1)[-1]}")
    desfecho = evento["outcome"]
    if evento.get("status"):
        desfecho += f" {evento['status']}"
    if evento.get("error"):
        desfecho += f" {evento['error']}"
    return " ".join(partes), desfecho


def desenhar(raizes):
    if not raizes:
        return []
    origem = min(raiz.evento["start_ms"] for raiz in raizes)
    linhas = []

    def visitar(no, profundidade):
        rotulo, desfecho = descrever(no.evento)
        deslocamento = no.evento["start_ms"] - origem
        linhas.append(
            f"{deslocamento:+8.1f} ms {'  ' * profundidade}{rotulo:<62} {no.evento['duration_ms']:>8.1f} ms  {desfecho}"
        )
        for filho in no.filhos:
            visitar(filho, profundidade + 1)

    for raiz in raizes:
        visitar(raiz, 0)
    return linhas


def mensagens_repetidas(eventos, servico="acervo"):
    vistos = defaultdict(list)
    for evento in spans(eventos):
        if evento["service"] == servico and evento.get("span_kind") == "server":
            vistos[evento["message_id"]].append(evento["instance"])
    return {mensagem: instancias for mensagem, instancias in vistos.items() if len(instancias) > 1}


def orfaos(eventos):
    todos = spans(eventos)
    conhecidos = {s["span_id"] for s in todos}
    return [s for s in todos if s.get("parent_span_id") and s["parent_span_id"] not in conhecidos]


def tempo_por_servico(spans_da_operacao):
    acumulado = defaultdict(float)
    for evento in spans_da_operacao:
        if evento.get("span_kind") == "server":
            acumulado[evento["service"]] += evento["duration_ms"]
    return dict(acumulado)


def principal():
    analisador = argparse.ArgumentParser(description="Reconstrói traces a partir dos logs estruturados.")
    analisador.add_argument("logs", nargs="+")
    analisador.add_argument("--correlation-id")
    analisador.add_argument("--limite", type=int, default=3)
    argumentos = analisador.parse_args()

    grupos = agrupar_por_correlacao(ler_eventos(*argumentos.logs))
    escolhidos = [argumentos.correlation_id] if argumentos.correlation_id else list(grupos)[: argumentos.limite]
    for correlation_id in escolhidos:
        print(f"trace {correlation_id}")
        for linha in desenhar(montar_arvore(grupos.get(correlation_id, []))):
            print(linha)
        print()


if __name__ == "__main__":
    principal()
