import csv
import platform
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict
from datetime import datetime

import fastapi
import requests

from app import config
from experimentos import (
    e01_referencia,
    e02_atraso,
    e03_erro_e_retry,
    e04_indisponibilidade,
    e05_timeout_ambiguo,
    e06_retry_nao_idempotente,
    e07_tempestade_de_retries,
    e08_circuit_breaker,
    e09_falha_simultanea,
    e10_seguranca,
)
from experimentos.comum import Coletor, limpar_logs, percentil

cenarios = [
    e01_referencia,
    e02_atraso,
    e03_erro_e_retry,
    e04_indisponibilidade,
    e05_timeout_ambiguo,
    e06_retry_nao_idempotente,
    e07_tempestade_de_retries,
    e08_circuit_breaker,
    e09_falha_simultanea,
    e10_seguranca,
]

relatorio = config.pasta_de_docs / "04-evidencias.md"
metricas = config.pasta_de_logs / "tentativas.csv"


def selecionar(argumentos):
    if not argumentos:
        return cenarios
    pedidos = {item.upper() for item in argumentos}
    escolhidos = [modulo for modulo in cenarios if modulo.codigo in pedidos]
    if not escolhidos:
        disponiveis = ", ".join(modulo.codigo for modulo in cenarios)
        raise SystemExit(f"nenhum cenário corresponde a {argumentos}. Disponíveis: {disponiveis}")
    return escolhidos


def escapar(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ")


def gravar_metricas(coletor):
    metricas.parent.mkdir(parents=True, exist_ok=True)
    with metricas.open("w", encoding="utf-8", newline="") as arquivo:
        campos = ["cenario", "chamada", "correlacao", "tentativa", "destino", "duracao_ms", "status", "tipo_de_erro", "espera_s"]
        escritor = csv.DictWriter(arquivo, fieldnames=campos, extrasaction="ignore")
        escritor.writeheader()
        for item in coletor.tentativas:
            escritor.writerow(asdict(item))


def tabela_de_classificacao(coletor, escolhidos):
    linhas = [
        "## Tabela de classificação",
        "",
        "A coluna **Observação** traz apenas o que foi medido nesta execução. **Classificação** e **Conclusão** são "
        "inferências feitas a partir dessa observação e do modelo de falhas.",
        "",
        "| Cenário | Hipótese | Falha injetada | Observação (medida) | Classificação (inferência) | Conclusão (inferência) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for modulo in escolhidos:
        conclusao = coletor.conclusoes.get(modulo.codigo)
        linhas.append(
            f"| **{modulo.codigo}** {escapar(modulo.titulo)} | {escapar(modulo.hipotese)} | "
            f"{escapar(modulo.falha_injetada)} | {escapar(conclusao.observacao) if conclusao else 'não executado'} | "
            f"{escapar(modulo.classificacao)} | {escapar(conclusao.conclusao) if conclusao else '-'} |"
        )
    return linhas


def resumo_de_tentativas(coletor, escolhidos):
    linhas = [
        "## Métricas por cenário",
        "",
        "| Cenário | Chamadas | Tentativas | Tentativas com sucesso | Tipos de erro | p50 (ms) | p95 (ms) | máx (ms) |",
        "| --- | :-: | :-: | :-: | --- | ---: | ---: | ---: |",
    ]
    for modulo in escolhidos:
        tentativas = coletor.tentativas_do_cenario(modulo.codigo)
        if not tentativas:
            continue
        chamadas = len({item.correlacao for item in tentativas})
        sucesso = sum(item.tipo_de_erro == "-" for item in tentativas)
        tipos = Counter(item.tipo_de_erro for item in tentativas if item.tipo_de_erro != "-")
        duracoes = [item.duracao_ms for item in tentativas]
        linhas.append(
            f"| {modulo.codigo} | {chamadas} | {len(tentativas)} | {sucesso} | "
            f"{', '.join(f'{tipo} ({quantidade})' for tipo, quantidade in tipos.most_common()) or '-'} | "
            f"{percentil(duracoes, 0.5):.1f} | {percentil(duracoes, 0.95):.1f} | {max(duracoes):.1f} |"
        )
    return linhas


def tentativas_detalhadas(coletor, escolhidos):
    linhas = [
        "## Tentativas individuais",
        "",
        "Duração, resultado e tipo de erro de cada tentativa. Chamadas em lote (E01, parte de E03, E07 e a rodada sem "
        f"disjuntor do E08) aparecem só nas métricas acima e no arquivo `logs/{metricas.name}`.",
        "",
        "| Cenário | Chamada | Correlação | Nº | Duração (ms) | Status | Tipo de erro | Espera seguinte (s) |",
        "| --- | --- | --- | :-: | ---: | :-: | --- | ---: |",
    ]
    for modulo in escolhidos:
        for item in coletor.tentativas_do_cenario(modulo.codigo):
            if not item.detalhar:
                continue
            espera = f"{item.espera_s:.2f}" if item.espera_s else "-"
            linhas.append(
                f"| {item.cenario} | {escapar(item.chamada)} | `{item.correlacao}` | {item.tentativa} | "
                f"{item.duracao_ms:.1f} | {item.status} | {item.tipo_de_erro} | {espera} |"
            )
    return linhas


def verificacoes(coletor, escolhidos):
    linhas = ["## Verificações por cenário", ""]
    for modulo in escolhidos:
        linhas += [
            f"### {modulo.codigo} — {modulo.titulo}",
            "",
            f"**Hipótese:** {modulo.hipotese}",
            "",
            "| Verificação | Esperado | Obtido | Resultado | Análise |",
            "| --- | --- | --- | :-: | --- |",
        ]
        evidencias = coletor.do_cenario(modulo.codigo)
        if not evidencias:
            linhas.append("| - | - | - | - | cenário não executado |")
        for item in evidencias:
            marca = "ok" if item.sucesso else "**falhou**"
            linhas.append(
                f"| {escapar(item.verificacao)} | `{escapar(item.esperado)}` | `{escapar(item.obtido)}` | "
                f"{marca} | {escapar(item.analise)} |"
            )
        linhas.append("")
    return linhas


def gerar_relatorio(coletor, escolhidos, duracao):
    linhas = [
        "# Evidências dos experimentos",
        "",
        "> Documento gerado automaticamente por `experimentos/executar_todos.py`.",
        "> Não edite à mão: a próxima execução sobrescreve o arquivo.",
        "",
        f"Execução: {datetime.now().astimezone().isoformat(timespec='seconds')}  ",
        f"Duração total: {duracao:.1f} s  ",
        f"Python {platform.python_version()} · FastAPI {fastapi.__version__} · requests {requests.__version__} · "
        f"{platform.system()} {platform.release()}  ",
        f"Verificações: {coletor.total} — falhas: {len(coletor.falhas)} · Tentativas medidas: {len(coletor.tentativas)}",
        "",
        "---",
        "",
        *tabela_de_classificacao(coletor, escolhidos),
        "",
        *resumo_de_tentativas(coletor, escolhidos),
        "",
        *tentativas_detalhadas(coletor, escolhidos),
        "",
        "---",
        "",
        *verificacoes(coletor, escolhidos),
        "---",
        "",
        "## Logs brutos",
        "",
        "Cada servidor grava uma linha JSON por requisição em `logs/<cenario>-<servidor>.jsonl`, com instante, "
        "correlação (`X-Request-ID`), número da tentativa (`X-Tentativa`), método, caminho, status e duração "
        "interna. O cliente envia a mesma correlação em todas as tentativas de uma chamada, então o log do servidor "
        "mostra quais tentativas chegaram e como terminaram. As tentativas medidas no cliente ficam em "
        f"`logs/{metricas.name}`.",
        "",
    ]
    relatorio.parent.mkdir(parents=True, exist_ok=True)
    relatorio.write_text("\n".join(linhas), encoding="utf-8")


def main(argumentos=None):
    escolhidos = selecionar(argumentos if argumentos is not None else sys.argv[1:])
    limpar_logs()

    coletor = Coletor()
    inicio = time.monotonic()

    for modulo in escolhidos:
        print(f"{modulo.codigo} — {modulo.titulo}")
        try:
            modulo.executar(coletor)
        except Exception as erro:
            coletor.registrar(
                modulo.codigo,
                "cenário concluído sem erro de orquestração",
                "sem exceção",
                type(erro).__name__,
                f"Falha durante a execução: {erro}",
                sucesso=False,
            )
            traceback.print_exc()
        print()

    duracao = time.monotonic() - inicio
    gravar_metricas(coletor)
    gerar_relatorio(coletor, escolhidos, duracao)

    print("-" * 78)
    print(
        f"{coletor.total} verificações em {duracao:.1f}s — "
        f"{coletor.total - len(coletor.falhas)} ok, {len(coletor.falhas)} falhas"
    )
    print(f"{len(coletor.tentativas)} tentativas medidas, gravadas em {metricas.relative_to(config.raiz_do_projeto)}")
    print(f"Tabela de evidências gravada em {relatorio.relative_to(config.raiz_do_projeto)}")
    if coletor.falhas:
        print("\nVerificações que falharam:")
        for item in coletor.falhas:
            print(f"  {item.cenario} · {item.verificacao}: esperado {item.esperado}, obtido {item.obtido}")
    return 1 if coletor.falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
