import sys
import time
import traceback
from datetime import datetime

from app import config
from app.registro import limpar_logs
from experimentos import (
    comum,
    e01_desacoplamento,
    e02_qos,
    e03_retained,
    e04_last_will,
    e05_duplicacao,
    e06_backpressure,
    e07_indisponibilidade,
)
from experimentos.comum import Coletor, FalhaDeOrquestracao

CENARIOS = [
    e01_desacoplamento,
    e02_qos,
    e03_retained,
    e04_last_will,
    e05_duplicacao,
    e06_backpressure,
    e07_indisponibilidade,
]

RELATORIO = config.RAIZ_DO_PROJETO / "docs" / "04-evidencias.md"


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
    return str(texto).replace("|", "\\|")


def gerar_relatorio(coletor, cenarios, duracao):
    linhas = [
        "# Evidências dos experimentos",
        "",
        "> Documento gerado automaticamente por `experimentos/executar_todos.py`.",
        "> Não edite à mão: a próxima execução sobrescreve o arquivo.",
        "",
        f"Execução: {datetime.now().astimezone().isoformat(timespec='seconds')}  ",
        f"Duração total: {duracao:.1f} s  ",
        f"Broker: `eclipse-mosquitto:2` em `{config.BROKER_HOST}:{config.BROKER_PORTA}`  ",
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
        "Cada processo grava uma linha JSON por evento em `logs/<id-do-processo>.jsonl`.",
        "Os identificadores são prefixados pelo código do cenário, então os arquivos de",
        "cada experimento ficam isolados. A saída de console de cada processo fica em",
        "`logs/<id-do-processo>.saida.txt`.",
        "",
    ]

    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text("\n".join(linhas), encoding="utf-8")


def main(argumentos=None):
    cenarios = selecionar(argumentos if argumentos is not None else sys.argv[1:])

    print("Preparando o ambiente (Docker + Mosquitto)...")
    try:
        comum.preparar_ambiente()
    except FalhaDeOrquestracao as erro:
        raise SystemExit(f"\n{erro}\n")
    limpar_logs()
    print(f"Broker no ar em {config.BROKER_HOST}:{config.BROKER_PORTA}\n")

    coletor = Coletor()
    inicio = time.monotonic()

    for modulo in cenarios:
        print(f"{modulo.CODIGO} — {modulo.TITULO}")
        try:
            comum.garantir_broker()
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
    print(f"Tabela de evidências gravada em {RELATORIO.relative_to(config.RAIZ_DO_PROJETO)}")
    if coletor.falhas:
        print("\nVerificações que falharam:")
        for item in coletor.falhas:
            print(f"  {item.cenario} · {item.verificacao}: esperado {item.esperado}, obtido {item.obtido}")
    return 1 if coletor.falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
