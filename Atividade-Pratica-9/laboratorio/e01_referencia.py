import json
import statistics
import subprocess

from laboratorio.comum import Laboratorio, Relato, cabecalho_de_resumo, linha_de_resumo, num, pct
from laboratorio.processos import python, raiz
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import resumir
from medicao.traces import agrupar_por_correlacao, desenhar, montar_arvore

repeticoes = 3
aquecimento = 20
total = 300
caminho = "/v1/livros/1"


def tempo_de_servico_efetivo(eventos):
    valores = [e["servico_ms"] for e in eventos if e.get("service") == "acervo" and "servico_ms" in e]
    return statistics.fmean(valores) if valores else None


def executar():
    relato = Relato(
        "E01",
        "Referência, aquecimento e repetibilidade",
        "Como o sistema se comporta sem perturbação, quanto custa o primeiro acesso e o quanto a medição se repete?",
        "16.1, 16.4, 16.7",
        hipotese=(
            "As primeiras requisições depois de subir os processos são mais lentas que o regime estável "
            "(conexões novas, caminhos de código frios), e três execuções independentes do mesmo cenário "
            "produzem p50 com diferença menor que 20%."
        ),
        procedimento=[
            f"Subir a topologia do zero (balcão + 2 réplicas do acervo, 10 ms de serviço configurado).",
            f"Enviar {aquecimento + total} requisições `GET {caminho}` com 1 cliente, sem pausa entre elas.",
            f"Separar as {aquecimento} primeiras como aquecimento e resumir as {total} restantes.",
            f"Derrubar tudo e repetir {repeticoes} vezes, cada uma com processos novos.",
            "Na última repetição, rodar também o `medir_latencia.py` do material contra o mesmo endpoint.",
        ],
    )

    linhas_estaveis, linhas_frias, resumos, primeiras = [], [], [], []
    saida_do_material = ""
    traces = {}
    servico_efetivo = []

    for numero in range(1, repeticoes + 1):
        with Laboratorio(f"e01-rep{numero}") as lab:
            resultado = executar_carga(lab.url(caminho), concorrencia=1, total=total, aquecimento=aquecimento, timeout_s=5)
            if numero == repeticoes:
                processo = subprocess.run(
                    [python, "-m", "medicao.medir_latencia", lab.url(caminho)],
                    cwd=raiz, capture_output=True, text=True, timeout=120,
                )
                saida_do_material = processo.stdout.strip() or processo.stderr.strip()
                processo = subprocess.run(
                    [python, "-m", "medicao.variantes_de_cliente", lab.url(caminho), "100"],
                    cwd=raiz, capture_output=True, text=True, timeout=120,
                )
                variantes = json.loads(processo.stdout)
            eventos = lab.eventos()

        frias = resultado.aquecimento
        estaveis = resultado.medidas
        resumo = resumir(estaveis)
        resumo_frio = resumir(frias)
        resumos.append(resumo)
        primeiras.append(frias[0].duracao_ms)
        servico_efetivo.append(tempo_de_servico_efetivo(eventos))
        linhas_estaveis.append(linha_de_resumo(f"repetição {numero}", resumo, [pct(resumo["taxa_de_erro"])]))
        linhas_frias.append(
            [f"repetição {numero}", num(frias[0].duracao_ms), num(frias[1].duracao_ms), num(resumo_frio["media_ms"]), num(resumo["p50_ms"]), num(frias[0].duracao_ms / resumo["p50_ms"])]
        )
        if numero == 1:
            grupos = agrupar_por_correlacao(eventos)
            traces["primeira"] = desenhar(montar_arvore(grupos.get(frias[0].correlation_id, [])))
            traces["estavel"] = desenhar(montar_arvore(grupos.get(estaveis[len(estaveis) // 2].correlation_id, [])))

    relato.tabela(
        "Regime estável (aquecimento descartado)",
        cabecalho_de_resumo + ["erros"],
        linhas_estaveis,
        "Latência medida no cliente, ponta a ponta, só das requisições com sucesso. "
        "Vazão = sucessos ÷ janela entre o início da primeira e o fim da última requisição.",
    )
    relato.tabela(
        "Aquecimento: o custo das primeiras requisições",
        ["repetição", "1ª req. (ms)", "2ª req. (ms)", f"média das {aquecimento} primeiras (ms)", "p50 estável (ms)", "1ª ÷ p50"],
        linhas_frias,
    )
    relato.texto(
        "Trace da primeira requisição (repetição 1)",
        "\n".join(traces["primeira"]),
        codigo=True,
    )
    relato.texto(
        "Trace de uma requisição em regime estável (repetição 1)",
        "\n".join(traces["estavel"]),
        codigo=True,
    )

    p50s = [r["p50_ms"] for r in resumos]
    dispersao = (max(p50s) - min(p50s)) / statistics.median(p50s)
    efetivo = statistics.fmean(v for v in servico_efetivo if v is not None)
    relato.tabela(
        "Repetibilidade entre as execuções",
        ["medida", "mínimo", "máximo", "dispersão (máx − mín) ÷ mediana"],
        [
            ["p50 (ms)", num(min(p50s)), num(max(p50s)), pct(dispersao)],
            ["p95 (ms)", num(min(r["p95_ms"] for r in resumos)), num(max(r["p95_ms"] for r in resumos)), pct((max(r["p95_ms"] for r in resumos) - min(r["p95_ms"] for r in resumos)) / statistics.median(r["p95_ms"] for r in resumos))],
            ["vazão (req/s)", num(min(r["vazao_rps"] for r in resumos)), num(max(r["vazao_rps"] for r in resumos)), pct((max(r["vazao_rps"] for r in resumos) - min(r["vazao_rps"] for r in resumos)) / statistics.median(r["vazao_rps"] for r in resumos))],
        ],
        f"Tempo de serviço configurado no acervo: 10 ms. Tempo efetivo medido pelo próprio acervo: {num(efetivo)} ms. "
        "Os serviços ativam o relógio de 1 ms do Windows (`servicos/relogio.py`); sem isso, todo `asyncio.sleep` "
        "arredonda para múltiplos de ~15,6 ms e a latência inteira anda em degraus.",
    )
    relato.texto(
        "Saída do `medir_latencia.py` do material (mesmo endpoint, sistema já aquecido)",
        saida_do_material,
        codigo=True,
    )
    relato.tabela(
        "O instrumento também é medido: três formas de chamar o mesmo endpoint",
        ["forma da chamada (processo à parte, 100 chamadas)", "mediana (ms)", "conexão TCP"],
        [
            ["requests.get(url, timeout=1) — a do material", num(variantes["requests.get(url, timeout=1)"]), "nova a cada chamada"],
            ["requests.get(url)", num(variantes["requests.get(url)"]), "nova a cada chamada"],
            ["Session().get(url, timeout=1) — a do gerador de carga", num(variantes["Session().get(url, timeout=1)"]), "reaproveitada"],
        ],
        "Mesmo servidor, mesmo endpoint, mesmo momento. A diferença está inteira no cliente: `requests.get` cria uma "
        "sessão e uma conexão por chamada, e, neste Windows, abrir a conexão com timeout definido custa mais que sem. "
        "O script do material mede, portanto, serviço + abertura de conexão. Não é um erro, mas precisa estar declarado "
        "no procedimento, senão a comparação com outra ferramenta parece uma regressão do servidor.",
    )
    relato.texto(
        "O que o script do material não mede",
        "O script cumpre o papel de primeira medição, mas deixa de fora quatro coisas que a seção 16 pede: "
        "(1) não calcula vazão, porque não registra a janela de tempo; (2) soma no mesmo contador `erros` uma resposta "
        "HTTP 5xx (erro de aplicação, via `raise_for_status`) e uma conexão recusada ou um timeout (erro de transporte); "
        "(3) não separa aquecimento, então a primeira requisição entra na média; (4) não propaga identificador, "
        "então nenhuma amostra pode ser cruzada com o log do servidor. O gerador `medicao/carga.py` cobre os quatro pontos. "
        "O percentil do material usa `int(p/100 × n)` como índice; o deste laboratório usa o posto mais próximo "
        "(`ceil(p/100 × n)`), que nunca escolhe uma posição acima da pedida.",
    )

    for numero, resumo in enumerate(resumos, 1):
        relato.verificar(f"repetição {numero}: todas as requisições com sucesso", "0 erros", f"{resumo['n'] - resumo['sucessos']} erros", resumo["sucessos"] == resumo["n"])
    relato.verificar("dispersão do p50 entre as repetições", "< 20%", pct(dispersao), dispersao < 0.20)
    relato.verificar(
        "conexão reaproveitada mais rápida que conexão nova com timeout",
        "Session < requests.get(timeout=1)",
        f"{num(variantes['Session().get(url, timeout=1)'])} ms < {num(variantes['requests.get(url, timeout=1)'])} ms",
        variantes["Session().get(url, timeout=1)"] < variantes["requests.get(url, timeout=1)"],
    )
    relato.verificar("saída do script do material foi capturada", "linha 'p50'", "presente" if "p50" in saida_do_material else "ausente", "p50" in saida_do_material)

    razoes = [f / r["p50_ms"] for f, r in zip(primeiras, resumos)]
    frias_acima = sum(1 for f, r in zip(primeiras, resumos) if f > r["p95_ms"])
    confirmada = frias_acima == repeticoes and dispersao < 0.20
    relato.dados = {
        "resumos": resumos,
        "primeiras_ms": primeiras,
        "dispersao_p50": dispersao,
        "servico_efetivo_ms": efetivo,
        "variantes_de_cliente_ms": variantes,
        "primeiras_acima_do_p95": frias_acima,
        "hipotese_confirmada": confirmada,
    }
    custo_extra = [f - r["p50_ms"] for f, r in zip(primeiras, resumos)]
    explicacao_do_tamanho = (
        "O laboratório só libera a carga depois que cada processo responde ao health check, e isso já paga a importação "
        "dos módulos e a subida do servidor. O que sobra de frio é abrir as conexões TCP (cliente → balcão e balcão → acervo) "
        "e o primeiro uso de cada caminho de código, que no loopback custam milissegundos, não segundos. Fora do loopback (TLS, DNS, "
        "rede real) o custo seria bem maior, e de qualquer forma o aquecimento é separado em todos os experimentos seguintes, "
        "porque essas requisições pertencem a outro estado do sistema."
    )
    if frias_acima == repeticoes:
        leitura_do_frio = (
            f"A primeira requisição ficou acima do p95 estável nas {repeticoes} repetições "
            f"({num(min(razoes))} a {num(max(razoes))} vezes o p50), então essa parte da hipótese se confirmou, mas o efeito é "
            f"pequeno: de {num(min(custo_extra))} a {num(max(custo_extra))} ms a mais, e a segunda requisição já volta para perto "
            f"do regime estável. {explicacao_do_tamanho}"
        )
    else:
        leitura_do_frio = (
            f"A primeira requisição ficou acima do p95 estável em só {frias_acima} de {repeticoes} repetições "
            f"({num(min(razoes))} a {num(max(razoes))} vezes o p50), então essa parte da hipótese foi refutada: "
            f"o custo do frio some na variação normal. O motivo está no procedimento. {explicacao_do_tamanho}"
        )
    relato.conclusao = (
        f"Em regime estável, o p50 ficou entre {num(min(p50s))} e {num(max(p50s))} ms nas três execuções "
        f"(dispersão de {pct(dispersao)}), então a medição se repete. {leitura_do_frio} "
        "Os dois traces mostram o mesmo desenho: quase todo o tempo do balcão é a chamada ao acervo, e a diferença entre "
        "o span de cliente no balcão e o span de servidor no acervo é o custo do caminho entre os dois processos "
        "(serialização, loopback e o framework)."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
