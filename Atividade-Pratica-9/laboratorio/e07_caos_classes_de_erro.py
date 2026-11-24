import statistics
from collections import Counter

from laboratorio.comum import Laboratorio, Relato, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import resumir
from medicao.traces import mensagens_repetidas

timeout_ms = 250
atraso_s = 0.4


def janela(eventos, carga):
    de = carga.inicio_epoch_ms
    ate = de + carga.duracao_s * 1000
    return [e for e in eventos if e.get("start_ms") and de <= e["start_ms"] <= ate]


def o_que_o_cliente_viu(amostras):
    contagem = Counter(f"{a.classe.replace('_', ' ')} ({a.detalhe.replace('http_', 'HTTP ')})" if a.classe != "sucesso" else "sucesso" for a in amostras)
    return ", ".join(f"{quantidade}× {rotulo}" for rotulo, quantidade in contagem.most_common())


def o_que_o_balcao_viu(eventos):
    falhas = Counter(e["error"] for e in eventos if e.get("service") == "balcao" and e.get("outcome") == "transport_error")
    if not falhas:
        return "nenhuma falha de transporte"
    return ", ".join(f"{quantidade}× {tipo}" for tipo, quantidade in falhas.most_common())


def executar():
    relato = Relato(
        "E07",
        "Caos no canal e na borda: classes de erro",
        "A mesma indisponibilidade, provocada em lugares diferentes, chega ao cliente da mesma forma?",
        "16.2, 16.5, 18.1",
        hipotese=(
            "Não. Falhas atrás do balcão chegam ao cliente como erro de aplicação (o balcão responde 503 ou 504 e explica), "
            "ou nem chegam, se o failover resolver. Só a falha do próprio balcão chega como erro de transporte. Por isso o "
            "cliente precisa contar os dois tipos separadamente: eles indicam lugares e ações diferentes."
        ),
        procedimento=[
            "Um proxy TCP de falhas na frente de cada réplica do acervo. O balcão só conhece os proxies.",
            f"Balcão com timeout de leitura de {timeout_ms} ms, timeout de conexão de 150 ms e quarentena de 1 s.",
            "Seis fases em sequência, cada uma com sua carga: referência; acervo-a atrasado no canal; acervo-a em buraco "
            "negro (aceita a conexão e engole os bytes); as duas réplicas em buraco negro; as duas réplicas mortas com os "
            "proxies de pé; o balcão morto.",
            "Para cada fase, comparar o que o cliente viu com o que o balcão registrou no log.",
        ],
    )

    fases = []
    with Laboratorio(
        "e07",
        proxies=True,
        balcao={"BALCAO_TIMEOUT_MS": timeout_ms, "BALCAO_TIMEOUT_CONEXAO_MS": 150, "BALCAO_QUARENTENA_S": 1},
    ) as lab:
        url = lab.url("/v1/livros/7")
        proxy_a, proxy_b = lab.proxies

        def fase(nome, perturbacao, onde, total, concorrencia=2, timeout_s=3):
            carga = executar_carga(url, concorrencia=concorrencia, total=total, timeout_s=timeout_s)
            fases.append({"nome": nome, "perturbacao": perturbacao, "onde": onde, "carga": carga, "eventos": janela(lab.eventos(), carga)})

        fase("1. referência", "nenhuma", "-", 200)
        proxy_a.configurar("atrasar", atraso_s)
        fase("2. acervo-a lento", f"+{int(atraso_s * 1000)} ms na resposta do acervo-a", "canal", 200)
        proxy_a.configurar("buraco_negro")
        fase("3. acervo-a mudo", "proxy aceita e engole a requisição", "canal", 200)
        proxy_b.configurar("buraco_negro")
        fase("4. acervo mudo", "as duas réplicas em buraco negro", "canal", 30)
        proxy_a.configurar("repassar")
        proxy_b.configurar("repassar")
        for replica in lab.replicas:
            replica.matar()
        fase("5. acervo morto", "os dois processos do acervo mortos", "processo atrás do balcão", 30)
        lab.balcao.matar()
        fase("6. balcão morto", "processo do balcão morto", "borda", 10, concorrencia=1, timeout_s=5)

    linhas = []
    resumos = {}
    for item in fases:
        amostras = item["carga"].medidas
        resumo = resumir(amostras)
        resumos[item["nome"]] = resumo
        item["resumo"] = resumo
        item["mediana_total_ms"] = statistics.median(a.duracao_ms for a in amostras)
        linhas.append([
            item["nome"], item["perturbacao"], item["onde"], o_que_o_cliente_viu(amostras),
            num(item["mediana_total_ms"]), num(resumo["p99_ms"]), o_que_o_balcao_viu(item["eventos"]) if item["eventos"] else "sem log (balcão morto)",
        ])

    relato.tabela(
        "Cada falha, onde ela foi provocada e como apareceu",
        ["fase", "perturbação", "onde", "o cliente viu", "mediana até a resposta ou erro (ms)", "p99 dos sucessos (ms)", "o balcão registrou"],
        linhas,
        "\"Erro de aplicação\" = chegou uma resposta HTTP com status de erro. \"Erro de transporte\" = não chegou resposta "
        "nenhuma (conexão recusada, interrompida ou timeout). A coluna do balcão vem do log dele, nas tentativas ao acervo.",
    )

    por_nome = {f["nome"]: f for f in fases}
    lenta = por_nome["2. acervo-a lento"]
    repetidas_na_lenta = mensagens_repetidas(lenta["eventos"])
    atendidas_na_a = [
        e for e in lenta["eventos"]
        if e.get("service") == "acervo" and e.get("instance") == "acervo-a" and e.get("operation") == "consultar_livro" and e["outcome"] == "success"
    ]
    relato.tabela(
        "Trabalho desperdiçado na fase 2",
        ["medida", "valor"],
        [
            ["atendimentos com sucesso registrados pelo acervo-a", len(atendidas_na_a)],
            ["tentativas do balcão ao acervo-a que deram timeout", sum(1 for e in lenta["eventos"] if e.get("service") == "balcao" and e.get("error") == "timeout_leitura")],
            ["mensagens atendidas pelas duas réplicas", len(repetidas_na_lenta)],
        ],
        "O acervo-a respondeu com sucesso, mas a resposta ficou presa 400 ms no canal e chegou depois que o balcão já tinha "
        "desistido e repetido no acervo-b. O mesmo `message_id` nos logs das duas réplicas mostra o trabalho feito duas vezes.",
    )

    morta = por_nome["6. balcão morto"]
    relato.texto(
        "Leitura: 503 do balcão contra conexão recusada",
        f"Nas fases 4 e 5 o acervo inteiro estava indisponível, e o cliente recebeu uma resposta HTTP: 504 quando o acervo "
        f"não respondeu dentro do prazo (o balcão não sabe se a operação aconteceu) e 503 quando a conexão caiu sem resposta "
        "(o balcão tem certeza de que não foi atendida, e manda `Retry-After`). Nos dois casos quem respondeu está vivo, "
        "conhece o problema e diz o que fazer. Na fase 6 ninguém respondeu: o cliente só ficou sabendo pelo sistema operacional, "
        f"e no Windows isso levou {num(morta['mediana_total_ms'])} ms de mediana, porque uma conexão recusada no loopback ainda "
        "passa por novas tentativas de SYN. Erro de aplicação e erro de transporte não são graus diferentes do mesmo problema. "
        "O primeiro diz \"a dependência falhou\", o segundo diz \"não consegui nem falar com o serviço\", e cada um exige uma "
        "ação diferente (esperar e repetir contra investigar a borda). Somar os dois num contador só, como o script do "
        "material faz, joga essa informação fora.\n\n"
        f"Nas fases 2 e 3 a falha nem chegou ao cliente: o failover resolveu tudo, e o custo apareceu só na cauda (p99 de "
        f"{num(resumos['2. acervo-a lento']['p99_ms'])} e {num(resumos['3. acervo-a mudo']['p99_ms'])} ms contra "
        f"{num(resumos['1. referência']['p99_ms'])} ms da referência). Cada vez que a quarentena de 1 s expira, uma "
        f"requisição volta a tentar o acervo-a e paga os {timeout_ms} ms do timeout antes de trocar de réplica.",
    )

    def proporcao(nome, classe, detalhe=None):
        amostras = por_nome[nome]["carga"].medidas
        return sum(1 for a in amostras if a.classe == classe and (detalhe is None or a.detalhe == detalhe)) / len(amostras)

    relato.verificar("1. referência: tudo com sucesso", "100%", pct(proporcao("1. referência", "sucesso")), proporcao("1. referência", "sucesso") == 1)
    for nome in ("2. acervo-a lento", "3. acervo-a mudo"):
        relato.verificar(f"{nome}: failover esconde a falha do cliente", "100% sucesso", pct(proporcao(nome, "sucesso")), proporcao(nome, "sucesso") == 1)
        timeouts = sum(1 for e in por_nome[nome]["eventos"] if e.get("service") == "balcao" and e.get("error") == "timeout_leitura")
        relato.verificar(f"{nome}: o balcão registrou os timeouts", "> 0", timeouts, timeouts > 0)
    relato.verificar("4. acervo mudo: cliente recebe 504", "100% HTTP 504", pct(proporcao("4. acervo mudo", "erro_aplicacao", "http_504")), proporcao("4. acervo mudo", "erro_aplicacao", "http_504") == 1)
    relato.verificar("5. acervo morto: cliente recebe 503", "100% HTTP 503", pct(proporcao("5. acervo morto", "erro_aplicacao", "http_503")), proporcao("5. acervo morto", "erro_aplicacao", "http_503") == 1)
    relato.verificar("6. balcão morto: cliente vê erro de transporte", "100% transporte", pct(proporcao("6. balcão morto", "erro_transporte")), proporcao("6. balcão morto", "erro_transporte") == 1)
    relato.verificar("fase 2: trabalho repetido detectado pelo message_id", "> 0", len(repetidas_na_lenta), len(repetidas_na_lenta) > 0)

    relato.dados = {
        "fases": [
            {"nome": f["nome"], "resumo": f["resumo"], "mediana_total_ms": f["mediana_total_ms"], "balcao": o_que_o_balcao_viu(f["eventos"])}
            for f in fases
        ],
        "repetidas_na_fase_2": len(repetidas_na_lenta),
    }
    relato.conclusao = (
        f"{relato.veredito()} Seis perturbações produziram quatro observações diferentes no cliente: sucesso com cauda maior "
        "(fases 2 e 3), 504 (fase 4), 503 (fase 5) e erro de transporte (fase 6). A classificação no cliente diz onde procurar, "
        "e a correlação com o log do balcão diz o que aconteceu do outro lado. Isso só funciona se as duas coisas forem "
        "registradas desde o início: separar erro de aplicação de erro de transporte, e propagar o identificador da operação."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
