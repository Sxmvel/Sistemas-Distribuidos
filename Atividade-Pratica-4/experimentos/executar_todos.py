import platform
import sys
import time
import traceback
from datetime import datetime

import grpc

from app import config
from app.registro import limpar_logs
from experimentos import (
    e01_contrato_e_fluxo,
    e02_erros,
    e03_deadlines,
    e04_indisponibilidade,
    e05_concorrencia,
    e06_retry_idempotencia,
    e07_evolucao_contrato,
)
from experimentos.comum import Coletor

CENARIOS = [
    e01_contrato_e_fluxo,
    e02_erros,
    e03_deadlines,
    e04_indisponibilidade,
    e05_concorrencia,
    e06_retry_idempotencia,
    e07_evolucao_contrato,
]

RELATORIO = config.PASTA_DE_DOCS / "04-evidencias.md"


def selecionar(argumentos):
    if not argumentos:
        return CENARIOS
    pedidos = {item.upper() for item in argumentos}
    escolhidos = [modulo for modulo in CENARIOS if modulo.CODIGO in pedidos]
    if not escolhidos:
        disponiveis = ", ".join(modulo.CODIGO for modulo in CENARIOS)
        raise SystemExit(f"nenhum cenário corresponde a {argumentos}. Disponíveis: {disponiveis}")
    return escolhidos


def escapar(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ")


def gerar_relatorio(coletor, cenarios, duracao):
    linhas = [
        "# Evidências dos experimentos",
        "",
        "> Documento gerado automaticamente por `experimentos/executar_todos.py`.",
        "> Não edite à mão: a próxima execução sobrescreve o arquivo.",
        "",
        f"Execução: {datetime.now().astimezone().isoformat(timespec='seconds')}  ",
        f"Duração total: {duracao:.1f} s  ",
        f"Python {platform.python_version()} · grpcio {grpc.__version__} · {platform.system()}  ",
        f"Verificações: {coletor.total} — falhas: {len(coletor.falhas)}",
        "",
        "## Resumo por cenário",
        "",
        "| Cenário | Título | Verificações | Falhas |",
        "| --- | --- | :-: | :-: |",
    ]

    for modulo in cenarios:
        evidencias = coletor.do_cenario(modulo.CODIGO)
        falhas = [item for item in evidencias if not item.sucesso]
        linhas.append(
            f"| {modulo.CODIGO} | {escapar(modulo.TITULO)} | {len(evidencias)} | {len(falhas)} |"
        )

    todas = coletor.medicoes
    if todas:
        linhas += [
            "",
            "## Latência e status por chamada",
            "",
            "| Cenário | Chamada | Deadline | Status | Latência (ms) | Observação |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
        for item in todas:
            linhas.append(
                f"| {item.cenario} | {escapar(item.chamada)} | {item.deadline} | "
                f"`{item.status}` | {item.latencia_ms:.1f} | {escapar(item.observacao)} |"
            )

    linhas += ["", "---", ""]

    for modulo in cenarios:
        evidencias = coletor.do_cenario(modulo.CODIGO)
        linhas += [
            f"## {modulo.CODIGO} — {modulo.TITULO}",
            "",
            f"**Pergunta que o cenário responde:** {modulo.PERGUNTA}",
            "",
            "| Verificação | Esperado | Obtido | Resultado | Análise |",
            "| --- | --- | --- | :-: | --- |",
        ]
        if not evidencias:
            linhas.append("| — | — | — | — | cenário não executado |")
        for item in evidencias:
            marca = "ok" if item.sucesso else "**falhou**"
            linhas.append(
                f"| {escapar(item.verificacao)} | `{escapar(item.esperado)}` | "
                f"`{escapar(item.obtido)}` | {marca} | {escapar(item.analise)} |"
            )
        linhas.append("")

    linhas += [
        "---",
        "",
        "## Logs brutos",
        "",
        "Cada processo grava uma linha JSON por evento em `logs/<id-do-processo>.jsonl`",
        "e a saída de console em `logs/<id-do-processo>.saida.txt`. Os identificadores são",
        "prefixados pelo código do cenário, então os arquivos de cada experimento ficam",
        "isolados. O interceptador do servidor registra `chamada-recebida` e",
        "`chamada-concluida` com método, status, latência e id de correlação; o",
        "interceptador do cliente registra `resposta-recebida` com o mesmo id.",
        "",
    ]

    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text("\n".join(linhas), encoding="utf-8")


def main(argumentos=None):
    cenarios = selecionar(argumentos if argumentos is not None else sys.argv[1:])
    limpar_logs()

    coletor = Coletor()
    inicio = time.monotonic()

    for modulo in cenarios:
        print(f"{modulo.CODIGO} — {modulo.TITULO}")
        try:
            modulo.executar(coletor)
        except Exception as erro:
            coletor.registrar(
                modulo.CODIGO,
                "cenario concluido sem erro de orquestracao",
                "sem excecao",
                type(erro).__name__,
                f"Falha durante a execucao: {erro}",
                sucesso=False,
            )
            traceback.print_exc()
        print()

    duracao = time.monotonic() - inicio
    gerar_relatorio(coletor, cenarios, duracao)

    print("-" * 78)
    print(
        f"{coletor.total} verificações em {duracao:.1f}s — "
        f"{coletor.total - len(coletor.falhas)} ok, {len(coletor.falhas)} falhas"
    )
    print(f"{len(coletor.medicoes)} medições de latência/status registradas")
    print(f"Tabela de evidências gravada em {RELATORIO.relative_to(config.RAIZ_DO_PROJETO)}")
    if coletor.falhas:
        print("\nVerificações que falharam:")
        for item in coletor.falhas:
            print(
                f"  {item.cenario} · {item.verificacao}: "
                f"esperado {item.esperado}, obtido {item.obtido}"
            )
    return 1 if coletor.falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
