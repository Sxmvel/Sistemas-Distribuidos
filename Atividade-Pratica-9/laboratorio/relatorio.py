import json

from laboratorio.comum import pasta_de_entrega, pasta_de_evidencias, raiz

destino = pasta_de_entrega / "docs" / "02-evidencias.md"


def celula(valor):
    return str(valor).replace("|", "\\|").replace("\n", " ")


def tabela_markdown(cabecalho, linhas):
    saida = ["| " + " | ".join(celula(c) for c in cabecalho) + " |", "| " + " | ".join("---" for _ in cabecalho) + " |"]
    saida += ["| " + " | ".join(celula(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def carregar():
    return [json.loads(caminho.read_text(encoding="utf-8")) for caminho in sorted(pasta_de_evidencias.glob("e*.json"))]


def secao(relato):
    partes = [f"## {relato['codigo']} — {relato['titulo']}", ""]
    partes += [f"**Pergunta:** {relato['pergunta']}", "", f"**Seções do material:** {relato['secoes_do_material']}", ""]
    if relato["hipotese"]:
        partes += [f"**Hipótese:** {relato['hipotese']}", ""]
    if relato["procedimento"]:
        partes += ["**Procedimento:**", ""] + [f"{i}. {passo}" for i, passo in enumerate(relato["procedimento"], 1)] + [""]
    for bloco in relato["blocos"]:
        partes += [f"### {bloco['titulo']}", ""]
        if bloco["tipo"] == "tabela":
            partes += [tabela_markdown(bloco["cabecalho"], bloco["linhas"]), ""]
            if bloco["nota"]:
                partes += [bloco["nota"], ""]
        elif bloco["tipo"] == "codigo":
            partes += ["```text", bloco["conteudo"], "```", ""]
        else:
            partes += [bloco["conteudo"], ""]
    verificacoes = relato["verificacoes"]
    if verificacoes:
        aprovadas = sum(1 for v in verificacoes if v["sucesso"])
        partes += [f"### Verificações ({aprovadas}/{len(verificacoes)})", ""]
        partes += [
            tabela_markdown(
                ["verificação", "esperado", "obtido", "resultado"],
                [[v["descricao"], v["esperado"], v["obtido"], "ok" if v["sucesso"] else "**falhou**"] for v in verificacoes],
            ),
            "",
        ]
    if relato["conclusao"]:
        partes += [f"**Conclusão:** {relato['conclusao']}", ""]
    ambiente = relato["ambiente"]
    partes += [f"<sub>Executado em {ambiente['data']} · Python {ambiente['python']} · {ambiente['sistema']}</sub>", ""]
    return "\n".join(partes)


def gerar():
    relatos = carregar()
    total = sum(len(r["verificacoes"]) for r in relatos)
    aprovadas = sum(1 for r in relatos for v in r["verificacoes"] if v["sucesso"])
    cabecalho = [
        "# Evidências dos experimentos",
        "",
        "Arquivo gerado por `python -m laboratorio.executar_todos` a partir de `entregavel/evidencias/*.json`. "
        "Não edite à mão: rode os experimentos de novo.",
        "",
        f"**Verificações aprovadas:** {aprovadas}/{total}",
        "",
        tabela_markdown(
            ["experimento", "pergunta", "verificações"],
            [
                [f"[{r['codigo']}](#{r['codigo'].lower()}--{ancora(r['titulo'])})", r["pergunta"], f"{sum(1 for v in r['verificacoes'] if v['sucesso'])}/{len(r['verificacoes'])}"]
                for r in relatos
            ],
        ),
        "",
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(cabecalho) + "\n" + "\n".join(secao(r) for r in relatos), encoding="utf-8")
    print(f"\nrelatório: {destino.relative_to(raiz)} ({aprovadas}/{total} verificações)")
    return aprovadas, total


def ancora(titulo):
    permitidos = []
    for caractere in titulo.lower():
        if caractere.isalnum():
            permitidos.append(caractere)
        elif caractere in " -":
            permitidos.append("-")
    return "".join(permitidos)


if __name__ == "__main__":
    gerar()
