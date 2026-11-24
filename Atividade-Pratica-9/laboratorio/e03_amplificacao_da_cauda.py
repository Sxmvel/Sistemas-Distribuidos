import math

from laboratorio.comum import Laboratorio, Relato, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import fracao_acima, resumir

prob_lentidao = 0.02
atraso_lento_ms = 300
limite_ms = 250
total = 500
concorrencia = 2
leques = (1, 5, 10)


def caminho_para(leque):
    return "/v1/livros/3" if leque == 1 else f"/v1/vitrine?quantidade={leque}"


def executar():
    relato = Relato(
        "E03",
        "Amplificação da cauda em chamadas compostas",
        "Se cada dependência é lenta raramente, com que frequência uma operação que chama várias delas é lenta?",
        "16.6",
        hipotese=(
            f"Com cada chamada ao acervo lenta com probabilidade p = {pct(prob_lentidao, 0)}, uma operação que espera n chamadas "
            "em paralelo é lenta com probabilidade 1 − (1 − p)^n: cerca de 2% para n = 1, 9,6% para n = 5 e 18,3% para n = 10."
        ),
        procedimento=[
            f"Acervo com {pct(prob_lentidao, 0)} das chamadas atrasadas em {atraso_lento_ms} ms (semente fixa por réplica) e 64 trabalhadores, para não haver fila.",
            "n = 1: `GET /v1/livros/3`, uma chamada ao acervo por requisição.",
            "n = 5 e n = 10: `GET /v1/vitrine?quantidade=n`, que dispara n chamadas em paralelo e só responde quando todas voltam.",
            f"{total} requisições medidas por cenário, {concorrencia} clientes. Lenta = acima de {limite_ms} ms no cliente.",
            "Comparar a fração observada com a prevista, usando 3 desvios-padrão da binomial como tolerância.",
        ],
    )

    ambiente = {
        "ACERVO_TEMPO_SERVICO_MS": 10,
        "ACERVO_TRABALHADORES": 64,
        "ACERVO_PROB_LENTIDAO": prob_lentidao,
        "ACERVO_ATRASO_LENTO_MS": atraso_lento_ms,
    }
    resultados = {}
    with Laboratorio(
        "e03",
        acervo=ambiente,
        por_replica=[{"ACERVO_SEMENTE": 11}, {"ACERVO_SEMENTE": 12}],
        balcao={"BALCAO_TIMEOUT_MS": 3000},
    ) as lab:
        for leque in leques:
            carga = executar_carga(lab.url(caminho_para(leque)), concorrencia=concorrencia, total=total, aquecimento=20, timeout_s=5)
            resultados[leque] = carga.medidas

    linhas = []
    dados = {}
    for leque in leques:
        amostras = resultados[leque]
        resumo = resumir(amostras)
        prevista = 1 - (1 - prob_lentidao) ** leque
        observada = fracao_acima(amostras, limite_ms)
        desvio = math.sqrt(prevista * (1 - prevista) / resumo["sucessos"])
        dados[leque] = {"resumo": resumo, "prevista": prevista, "observada": observada, "desvio": desvio}
        linhas.append([
            leque, resumo["n"], num(resumo["p50_ms"]), num(resumo["p95_ms"]), num(resumo["p99_ms"]),
            pct(prevista), pct(observada), f"± {pct(3 * desvio)}",
        ])

    relato.tabela(
        "Fração de operações lentas conforme o número de chamadas",
        ["chamadas (n)", "amostras", "p50 (ms)", "p95 (ms)", "p99 (ms)", "lentas previstas", "lentas observadas", "tolerância (3σ)"],
        linhas,
        f"Lenta = latência no cliente acima de {limite_ms} ms. Previsão: 1 − (1 − {num(prob_lentidao, 2)})^n.",
    )
    relato.texto(
        "Leitura",
        f"Com uma chamada, a lentidão fica fora do p95 (como no E02). Com {leques[1]} chamadas em paralelo, "
        f"{pct(dados[leques[1]]['observada'])} das operações já são lentas e o p95 passa a mostrar o atraso: "
        f"{num(dados[leques[1]]['resumo']['p95_ms'])} ms. Com {leques[2]}, {pct(dados[leques[2]]['observada'])}. Nenhuma réplica ficou pior, "
        "a diferença é só quantas vezes cada operação \"tira na loteria\" da lentidão. Em sistemas compostos, o p99 de cada "
        "dependência vira o p90 ou o p80 do serviço que as combina. Mitigações conhecidas: limitar o leque, usar respostas "
        "parciais com prazo, ou disparar uma requisição de reserva quando a primeira demora mais que o p95 (*hedged request*).",
    )

    for leque in leques:
        item = dados[leque]
        tolerancia = 3 * item["desvio"] + 0.005
        relato.verificar(
            f"n = {leque}: fração observada dentro da tolerância",
            f"{pct(item['prevista'])} ± {pct(tolerancia)}",
            pct(item["observada"]),
            abs(item["observada"] - item["prevista"]) <= tolerancia,
        )
        relato.verificar(f"n = {leque}: nenhuma operação falhou", "0 erros", f"{item['resumo']['n'] - item['resumo']['sucessos']} erros", item["resumo"]["sucessos"] == item["resumo"]["n"])
    crescente = dados[leques[0]]["observada"] < dados[leques[1]]["observada"] < dados[leques[2]]["observada"]
    relato.verificar("fração de lentas cresce com n", "crescente", " < ".join(pct(dados[l]["observada"]) for l in leques), crescente)
    relato.verificar(
        f"com n = {leques[1]}, o p95 já mostra a lentidão",
        f"> {limite_ms} ms",
        f"{num(dados[leques[1]]['resumo']['p95_ms'])} ms",
        dados[leques[1]]["resumo"]["p95_ms"] > limite_ms,
    )

    relato.dados = {str(k): v for k, v in dados.items()}
    relato.conclusao = (
        f"{relato.veredito()} A mesma réplica, lenta em {pct(prob_lentidao, 0)} das chamadas, produziu "
        f"{pct(dados[1]['observada'])}, {pct(dados[5]['observada'])} e {pct(dados[10]['observada'])} de operações lentas para "
        "1, 5 e 10 chamadas. A cauda de uma dependência se amplifica no serviço que espera por várias delas, e é por isso "
        "que medir o p99 de cada componente isolado não basta: é preciso medir a operação que o usuário executa, ponta a ponta."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
