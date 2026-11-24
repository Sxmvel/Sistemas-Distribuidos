from laboratorio.comum import Laboratorio, Relato, cabecalho_de_resumo, linha_de_resumo, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import fracao_acima, resumir

concorrencia = 4
total = 1000
aquecimento = 50
prob_lentidao = 0.02
atraso_lento_ms = 500
slo_ms = 100
limite_de_lentidao_ms = 200
caminho = "/v1/livros/2"


def medir(rotulo, ambiente_do_acervo):
    with Laboratorio(f"e02-{rotulo}", acervo=ambiente_do_acervo, balcao={"BALCAO_TIMEOUT_MS": 3000}) as lab:
        resultado = executar_carga(lab.url(caminho), concorrencia=concorrencia, total=total, aquecimento=aquecimento, timeout_s=5)
    return resultado.medidas


def executar():
    relato = Relato(
        "E02",
        "Média contra percentis",
        "Uma média boa garante que os usuários estão bem atendidos?",
        "16.2, 16.6",
        hipotese=(
            f"Se {pct(prob_lentidao, 0)} das requisições ganharem {atraso_lento_ms} ms de atraso, a média continua abaixo de "
            f"um objetivo de {slo_ms} ms e o p50 e o p95 quase não mudam, mas o p99 passa de {atraso_lento_ms} ms."
        ),
        procedimento=[
            f"Cenário de base: acervo sem perturbação, {concorrencia} clientes, {total} requisições medidas depois de {aquecimento} de aquecimento.",
            f"Cenário com cauda: o acervo sorteia (semente fixa) {pct(prob_lentidao, 0)} das requisições para atrasar {atraso_lento_ms} ms a mais.",
            "O balcão tem timeout de 3 s, para nenhuma requisição lenta virar erro e sair da distribuição.",
            "Comparar média, p50, p95, p99, máximo e a fração de requisições acima de 200 ms.",
        ],
    )

    base = medir("base", {"ACERVO_TEMPO_SERVICO_MS": 10})
    cauda = medir(
        "cauda",
        {
            "ACERVO_TEMPO_SERVICO_MS": 10,
            "ACERVO_PROB_LENTIDAO": prob_lentidao,
            "ACERVO_ATRASO_LENTO_MS": atraso_lento_ms,
            "ACERVO_SEMENTE": 42,
        },
    )
    resumo_base = resumir(base, slo_ms=slo_ms)
    resumo_cauda = resumir(cauda, slo_ms=slo_ms)
    lentas_base = fracao_acima(base, limite_de_lentidao_ms)
    lentas_cauda = fracao_acima(cauda, limite_de_lentidao_ms)

    relato.tabela(
        "Distribuição da latência nos dois cenários",
        cabecalho_de_resumo + [f"> {limite_de_lentidao_ms} ms", f"disponibilidade (≤ {slo_ms} ms)"],
        [
            linha_de_resumo("base", resumo_base, [pct(lentas_base), pct(resumo_base["disponibilidade"])]),
            linha_de_resumo(f"{pct(prob_lentidao, 0)} lentas", resumo_cauda, [pct(lentas_cauda), pct(resumo_cauda["disponibilidade"])]),
        ],
        "Disponibilidade observada = fração das requisições que tiveram sucesso dentro do objetivo de tempo (seção 16.2).",
    )

    def razao(campo):
        return resumo_cauda[campo] / resumo_base[campo]

    relato.tabela(
        "Quanto cada medida mudou",
        ["medida", "base (ms)", "com cauda (ms)", "razão"],
        [[campo.replace("_ms", ""), num(resumo_base[campo]), num(resumo_cauda[campo]), f"{num(razao(campo), 2)}×"] for campo in ("media_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms")],
    )
    relato.texto(
        "Leitura",
        f"Quem olhasse só a média veria {num(resumo_cauda['media_ms'])} ms, abaixo do objetivo de {slo_ms} ms, e concluiria que está tudo bem. "
        f"O p99 mostra o contrário: cerca de uma em cada {round(1 / lentas_cauda)} requisições espera mais de meio segundo, "
        f"e o p99 ficou {num(razao('p99_ms'), 1)} vezes maior que o de base. "
        f"O p95 quase não se move ({num(razao('p95_ms'), 2)}×): ele é o valor na posição 95% da lista ordenada, e as "
        f"{pct(lentas_cauda)} lentas ocupam só as posições acima de {pct(1 - lentas_cauda)}. Abaixo dele ainda está tudo normal. "
        f"Uma cauda que atinge f% das requisições só aparece nos percentis acima de 100 − f. "
        "Por isso o objetivo de serviço é escrito como \"99% abaixo de X ms\", e não como uma média.\n\n"
        f"A vazão também caiu, de {num(resumo_base['vazao_rps'])} para {num(resumo_cauda['vazao_rps'])} req/s, sem o servidor estar "
        "sobrecarregado. O gerador é de malha fechada: cada cliente só envia a próxima requisição quando a anterior "
        "termina, então um cliente preso numa requisição lenta deixa de gerar carga. Aqui isso não distorce a distribuição, "
        "porque a lentidão é sorteada por requisição e não atrasa as outras. Se o servidor inteiro travasse, porém, a malha "
        "fechada pararia de enviar justamente durante o travamento e mediria poucas amostras ruins (*coordinated omission*). "
        "Usuários reais não esperam uns pelos outros, então a carga continuaria chegando e a cauda real seria maior que a medida.",
    )

    relato.verificar("base: todas com sucesso", "0 erros", f"{resumo_base['n'] - resumo_base['sucessos']} erros", resumo_base["sucessos"] == resumo_base["n"])
    relato.verificar("cauda: todas com sucesso (nenhuma lenta virou erro)", "0 erros", f"{resumo_cauda['n'] - resumo_cauda['sucessos']} erros", resumo_cauda["sucessos"] == resumo_cauda["n"])
    relato.verificar("fração de lentas próxima da sorteada", "entre 1% e 3,5%", pct(lentas_cauda), 0.01 <= lentas_cauda <= 0.035)
    relato.verificar(f"média com cauda continua abaixo de {slo_ms} ms", f"< {slo_ms} ms", f"{num(resumo_cauda['media_ms'])} ms", resumo_cauda["media_ms"] < slo_ms)
    relato.verificar("p50 praticamente igual", "razão entre 0,8 e 1,2", num(razao("p50_ms"), 2), 0.8 <= razao("p50_ms") <= 1.2)
    relato.verificar("p95 praticamente igual", "razão entre 0,8 e 1,3", num(razao("p95_ms"), 2), 0.8 <= razao("p95_ms") <= 1.3)
    relato.verificar(f"p99 com cauda passa de {atraso_lento_ms} ms", f"> {atraso_lento_ms} ms", f"{num(resumo_cauda['p99_ms'])} ms", resumo_cauda["p99_ms"] > atraso_lento_ms)

    relato.dados = {"base": resumo_base, "cauda": resumo_cauda, "lentas_base": lentas_base, "lentas_cauda": lentas_cauda}
    relato.conclusao = (
        f"{relato.veredito()} Com {pct(lentas_cauda)} de requisições lentas, a média subiu de {num(resumo_base['media_ms'])} para "
        f"{num(resumo_cauda['media_ms'])} ms e continuou \"boa\", o p95 ficou em {num(resumo_cauda['p95_ms'])} ms, e o p99 saltou de "
        f"{num(resumo_base['p99_ms'])} para {num(resumo_cauda['p99_ms'])} ms. A média mistura as duas populações e esconde a segunda: "
        "o p99 é a única medida da tabela que separa \"o sistema está lento\" de \"o sistema está lento para alguns\"."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
