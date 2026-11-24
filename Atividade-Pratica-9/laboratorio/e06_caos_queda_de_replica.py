from collections import Counter

from laboratorio.comum import Laboratorio, Relato, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import linha_do_tempo, resumir

concorrencia = 4
duracao_s = 16
instante_da_queda_s = 5
instante_da_volta_s = 10
slo_ms = 250
limite_de_aborto = 0.2
disponibilidade_minima = 0.99
quarentena_s = 2


def executar():
    relato = Relato(
        "E06",
        "Caos: queda de uma réplica sob carga",
        "O sistema mantém o estado estável quando uma réplica do acervo morre no meio da carga?",
        "16.5",
        hipotese=(
            f"Estado estável = disponibilidade observada (sucesso em até {slo_ms} ms) de pelo menos {pct(disponibilidade_minima, 0)}. "
            f"Matar a réplica acervo-a com {concorrencia} clientes ativos não tira o sistema do estado estável, porque o balcão "
            f"troca de réplica na falha e deixa a réplica morta {quarentena_s} s em quarentena. Nenhum erro chega ao cliente."
        ),
        procedimento=[
            f"Topologia normal: balcão com timeout de conexão de 150 ms, timeout de leitura de 1 s e quarentena de {quarentena_s} s.",
            f"Carga constante de {concorrencia} clientes durante {duracao_s} s em `GET /v1/livros/6`.",
            f"Em t = {instante_da_queda_s} s, matar o processo do acervo-a (`kill`, sem desligamento limpo).",
            f"Em t = {instante_da_volta_s} s, subir o acervo-a de novo na mesma porta.",
            f"Critério de interrupção: se mais de {pct(limite_de_aborto, 0)} das requisições falharem em qualquer janela de 1 s, a carga para.",
        ],
    )

    with Laboratorio("e06", balcao={"BALCAO_TIMEOUT_MS": 1000, "BALCAO_TIMEOUT_CONEXAO_MS": 150, "BALCAO_QUARENTENA_S": quarentena_s}) as lab:
        replica = lab.replicas[0]
        carga = executar_carga(
            lab.url("/v1/livros/6"),
            concorrencia=concorrencia,
            duracao_s=duracao_s,
            timeout_s=5,
            limite_de_erro=limite_de_aborto,
            eventos=[(instante_da_queda_s, "acervo-a morto", replica.matar), (instante_da_volta_s, "acervo-a religado", replica.iniciar)],
        )
    eventos = lab.eventos()

    marcos = {m["rotulo"]: m for m in carga.marcos}
    queda = marcos.get("acervo-a morto", {}).get("inicio_s", instante_da_queda_s)
    volta = marcos.get("acervo-a religado", {}).get("fim_s", instante_da_volta_s)
    amostras = carga.amostras
    fases = {
        "antes da queda": [a for a in amostras if a.inicio_s < queda],
        "acervo-a fora": [a for a in amostras if queda <= a.inicio_s < volta],
        "depois da volta": [a for a in amostras if a.inicio_s >= volta],
    }
    resumos = {nome: resumir(lista, slo_ms=slo_ms) for nome, lista in fases.items()}

    tentativas_na_a = [
        e for e in eventos
        if e.get("service") == "balcao" and e.get("span_kind") == "client" and e.get("replica", "").endswith(":8201")
    ]
    falhas_na_a = [e for e in tentativas_na_a if e["outcome"] == "transport_error"]
    tipos = Counter(e["error"] for e in falhas_na_a)
    atendimentos_depois = [
        e for e in eventos
        if e.get("service") == "acervo" and e.get("instance") == "acervo-a" and e.get("operation") == "consultar_livro"
        and carga.relativo(e["start_ms"]) >= volta
    ]

    relato.tabela(
        "Marcos do experimento",
        ["evento", "início (s)", "fim (s)"],
        [[m["rotulo"], num(m["inicio_s"], 2), num(m["fim_s"], 2)] for m in carga.marcos]
        + ([["carga interrompida pelo critério de aborto", carga.motivo_do_aborto, ""]] if carga.abortado else []),
    )
    relato.tabela(
        "Estado estável por fase",
        ["fase", "requisições", "erros", "p50 (ms)", "p95 (ms)", "máx (ms)", f"disponibilidade (≤ {slo_ms} ms)", "estado estável"],
        [
            [nome, r["n"], r["n"] - r["sucessos"], num(r["p50_ms"]), num(r["p95_ms"]), num(r["max_ms"]), pct(r["disponibilidade"], 2),
             "mantido" if r["disponibilidade"] >= disponibilidade_minima else "**perdido**"]
            for nome, r in resumos.items()
        ],
    )

    falhas_por_segundo = Counter(int(carga.relativo(e["start_ms"])) for e in falhas_na_a)
    relato.tabela(
        "Linha do tempo (janelas de 1 s)",
        ["t (s)", "requisições", "erros no cliente", "p95 (ms)", "máx (ms)", "falhas do balcão no acervo-a"],
        [
            [f"{int(b['de_s'])}–{int(b['ate_s'])}", b["n"], b["n"] - b["sucessos"], num(b["p95_ms"]), num(b["max_ms"]), falhas_por_segundo.get(int(b["de_s"]), 0)]
            for b in linha_do_tempo(amostras, 1.0, slo_ms)
        ],
        "A última coluna vem do log do balcão: tentativas ao acervo-a que terminaram em erro de transporte naquele segundo.",
    )
    relato.tabela(
        "Como o balcão viu a réplica morta",
        ["tipo de falha", "ocorrências"],
        [[tipo, quantidade] for tipo, quantidade in tipos.most_common()] or [["nenhuma", 0]],
        "No Windows, conectar numa porta fechada do loopback leva ~2 s para ser recusado (o sistema repete o SYN). "
        "Com timeout de conexão de 150 ms, o balcão desiste antes, e a falha aparece como `timeout_conexao`, "
        "não como `conexao_recusada`. As requisições que estavam em andamento no momento do `kill` aparecem como `conexao_interrompida`.",
    )

    janela_fora = max(0.001, volta - queda)
    requisicoes_fora = resumos["acervo-a fora"]["n"]
    estavel = all(r["disponibilidade"] >= disponibilidade_minima for r in resumos.values())
    erros_no_cliente = sum(r["n"] - r["sucessos"] for r in resumos.values())
    relato.texto(
        "Leitura",
        f"Durante os {num(janela_fora)} s sem o acervo-a, o balcão atendeu {requisicoes_fora} requisições e tentou a réplica morta "
        f"só {len(falhas_na_a)} vezes. Sem quarentena, o rodízio mandaria metade delas para lá, e cada uma pagaria os 150 ms "
        "do timeout de conexão antes de trocar de réplica. A quarentena transforma uma degradação contínua em um custo "
        f"pontual a cada {quarentena_s} s, que aparece como degraus no máximo da linha do tempo. O p95 da fase com a réplica fora foi "
        f"{num(resumos['acervo-a fora']['p95_ms'])} ms, contra {num(resumos['antes da queda']['p95_ms'])} ms antes. "
        f"Depois de religada, o acervo-a voltou a receber tráfego ({len(atendimentos_depois)} atendimentos) sem nenhuma intervenção, "
        "porque a quarentena expira sozinha."
        + (
            f"\n\nAs falhas vêm em rajadas: o maior grupo teve {max(falhas_por_segundo.values())} tentativas no mesmo segundo, "
            f"com {concorrencia} clientes ativos. Quando a quarentena expira, todas as requisições em andamento consideram a réplica "
            "disponível de novo e a testam ao mesmo tempo. Um disjuntor com estado meio-aberto deixaria passar uma única "
            "requisição de teste e manteria as outras na réplica saudável."
            if falhas_por_segundo else ""
        ),
    )

    relato.verificar("o critério de aborto não disparou", "carga completa", carga.motivo_do_aborto or "carga completa", not carga.abortado)
    relato.verificar("os dois eventos de caos foram executados", "2 marcos", f"{len(carga.marcos)} marcos", len(carga.marcos) == 2)
    relato.verificar("nenhum erro chegou ao cliente", "0", erros_no_cliente, erros_no_cliente == 0)
    relato.verificar("o balcão percebeu a réplica morta", "> 0 falhas de transporte", len(falhas_na_a), len(falhas_na_a) > 0)
    relato.verificar(
        "quarentena evitou insistir na réplica morta",
        f"< 10% das {requisicoes_fora} requisições",
        f"{len(falhas_na_a)} ({pct(len(falhas_na_a) / max(1, requisicoes_fora))})",
        len(falhas_na_a) < 0.1 * max(1, requisicoes_fora),
    )
    relato.verificar("acervo-a voltou a atender depois de religado", "> 0 atendimentos", len(atendimentos_depois), len(atendimentos_depois) > 0)

    relato.dados = {
        "resumos": resumos,
        "marcos": carga.marcos,
        "falhas_na_a": len(falhas_na_a),
        "tipos": dict(tipos),
        "estado_estavel_mantido": estavel,
        "abortado": carga.abortado,
    }
    if estavel:
        veredito = "Hipótese confirmada: o estado estável se manteve nas três fases."
    else:
        perdidas = [nome for nome, r in resumos.items() if r["disponibilidade"] < disponibilidade_minima]
        veredito = (
            f"Hipótese refutada em parte: nenhum erro chegou ao cliente, mas a disponibilidade dentro de {slo_ms} ms ficou "
            f"abaixo de {pct(disponibilidade_minima, 0)} em: {', '.join(perdidas)}. O failover evita o erro, mas não o atraso."
        )
    relato.conclusao = (
        f"{veredito} Disponibilidade por fase: "
        + "; ".join(f"{nome} {pct(r['disponibilidade'], 2)}" for nome, r in resumos.items())
        + ". O experimento seguiu o roteiro da seção 16.5: hipótese escrita antes, perturbação controlada (um processo, "
        "num instante marcado), observação por fase e um critério de interrupção que pararia a carga se o dano passasse do limite."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
