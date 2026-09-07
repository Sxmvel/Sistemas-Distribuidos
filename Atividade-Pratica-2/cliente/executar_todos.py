import sys
from datetime import datetime
from pathlib import Path

from cliente.cenarios import (
    c01_fluxo_feliz,
    c02_validacao,
    c03_nao_encontrado,
    c04_conflito,
    c05_idempotencia,
    c06_concorrencia,
    c07_timeout,
    c08_conectividade,
)
from cliente.comum import BASE, TIMEOUT, Coletor, servidor_no_ar

CENARIOS = [
    c01_fluxo_feliz,
    c02_validacao,
    c03_nao_encontrado,
    c04_conflito,
    c05_idempotencia,
    c06_concorrencia,
    c07_timeout,
    c08_conectividade,
]

DESTINO = Path(__file__).resolve().parent.parent / "docs" / "04-evidencias.md"


def escapar(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ")


def gerar_documento(coletor):
    aprovados = coletor.total - len(coletor.falhas)
    linhas = [
        "# Evidências de teste",
        "",
        "> Documento gerado automaticamente por `cliente/executar_todos.py`.",
        f"> Execução em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} contra `{BASE}` "
        f"com timeout de {TIMEOUT}s no cliente.",
        "",
        f"**Resultado: {aprovados} de {coletor.total} verificações conforme o esperado.**",
        "",
        "---",
        "",
    ]

    for modulo in CENARIOS:
        evidencias = [e for e in coletor.evidencias if e.cenario == modulo.NOME]
        if not evidencias:
            continue
        linhas += [
            f"## {modulo.NOME}",
            "",
            f"{modulo.DESCRICAO}",
            "",
            "| Requisição | Esperado | Obtido | OK | Análise |",
            "| --- | --- | --- | :-: | --- |",
        ]
        for e in evidencias:
            marca = "✅" if e.sucesso else "❌"
            linhas.append(
                f"| `{escapar(e.requisicao)}` | {escapar(e.esperado)} | "
                f"{escapar(e.obtido)} | {marca} | {escapar(e.analise)} |"
            )
        linhas += ["", ""]

    return "\n".join(linhas)


def principal():
    if not servidor_no_ar():
        print(f"Servidor indisponível em {BASE}.")
        print("Suba a API antes de executar os cenários:")
        print("  .venv\\Scripts\\fastapi.exe dev app\\main.py")
        return 1

    coletor = Coletor()
    for modulo in CENARIOS:
        print(f"\n{modulo.NOME} - {modulo.DESCRICAO}")
        modulo.executar(coletor)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(gerar_documento(coletor), encoding="utf-8")

    aprovados = coletor.total - len(coletor.falhas)
    print(f"\n{'=' * 78}")
    print(f"{aprovados} de {coletor.total} verificações conforme o esperado.")
    print(f"Tabela de evidências gravada em {DESTINO}")
    return 0 if not coletor.falhas else 1


if __name__ == "__main__":
    sys.exit(principal())
