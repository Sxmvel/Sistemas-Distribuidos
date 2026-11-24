import json

from laboratorio.comum import Laboratorio, Relato, num, pct
from laboratorio.relatorio import gerar
from medicao.carga import executar_carga
from medicao.estatistica import resumir
from medicao.traces import agrupar_por_correlacao, desenhar, mensagens_repetidas, montar_arvore, orfaos

total = 60
prob_erro = 0.3


def executar():
    relato = Relato(
        "E05",
        "Correlação e trace distribuído",
        "Com três processos e uma réplica falhando, dá para reconstruir cada operação e ligar o erro interno à requisição externa?",
        "16.3, 16.8, 16.9",
        hipotese=(
            "Propagando `correlation_id`, `message_id`, `causation_id` e o span pai por cabeçalho, os logs dos três processos "
            "reconstroem 100% das operações, sem spans órfãos. Os erros que o failover esconde do cliente continuam visíveis e "
            "atribuíveis à requisição de origem, e a nova tentativa aparece como a mesma mensagem entregue a duas réplicas."
        ),
        procedimento=[
            f"Réplica acervo-a devolve 500 em {pct(prob_erro, 0)} das chamadas (semente fixa); acervo-b funciona normalmente.",
            f"O cliente envia {total} requisições `GET /v1/livros/5`, cada uma com `X-Correlation-ID` e `X-Message-ID` próprios.",
            "O balcão cria um span de servidor, um span de cliente por tentativa ao acervo, e repassa os identificadores.",
            "Juntar os logs JSON dos três processos, agrupar por `correlation_id` e montar a árvore pelos `parent_span_id`.",
        ],
    )

    with Laboratorio("e05", por_replica=[{"ACERVO_PROB_ERRO": prob_erro, "ACERVO_SEMENTE": 7}, {}]) as lab:
        carga = executar_carga(lab.url("/v1/livros/5"), concorrencia=1, total=total, timeout_s=5)
    eventos = lab.eventos()
    grupos = agrupar_por_correlacao(eventos)
    resumo = resumir(carga.medidas)

    ids_do_cliente = [a.correlation_id for a in carga.medidas]
    completos = 0
    for correlation_id in ids_do_cliente:
        spans_da_operacao = grupos.get(correlation_id, [])
        tem_balcao = any(s["service"] == "balcao" and s["span_kind"] == "server" for s in spans_da_operacao)
        tem_acervo = any(s["service"] == "acervo" for s in spans_da_operacao)
        completos += tem_balcao and tem_acervo

    sem_pai = orfaos(eventos)
    servidores_do_balcao = {
        s["correlation_id"]: s for s in eventos
        if s.get("service") == "balcao" and s.get("span_kind") == "server" and s["operation"] == "consultar_livro"
    }
    spans_do_acervo = [
        s for s in eventos
        if s.get("service") == "acervo" and s.get("span_kind") == "server" and s["operation"] == "consultar_livro"
    ]
    causas_corretas = sum(1 for s in spans_do_acervo if s["causation_id"] == servidores_do_balcao[s["correlation_id"]]["message_id"])
    erros_internos = [s for s in spans_do_acervo if s["outcome"] == "server_error"]
    classe_por_id = {a.correlation_id: a.classe for a in carga.medidas}
    mascarados = [s for s in erros_internos if classe_por_id.get(s["correlation_id"]) == "sucesso"]
    repetidas = mensagens_repetidas(eventos)

    relato.tabela(
        "O que os logs permitem reconstruir",
        ["medida", "valor"],
        [
            ["requisições do cliente", len(ids_do_cliente)],
            ["com sucesso no cliente", f"{resumo['sucessos']} ({pct(resumo['sucessos'] / resumo['n'], 0)})"],
            ["operações com spans no balcão e no acervo", f"{completos} de {len(ids_do_cliente)}"],
            ["spans com pai ausente (órfãos)", len(sem_pai)],
            ["spans do acervo cujo `causation_id` aponta a mensagem do balcão", f"{causas_corretas} de {len(spans_do_acervo)}"],
            ["erros 500 no acervo-a", len(erros_internos)],
            ["desses, invisíveis para o cliente (failover)", len(mascarados)],
            ["mensagens (`message_id`) recebidas por duas réplicas", len(repetidas)],
        ],
    )

    exemplo_limpo = next(c for c in ids_do_cliente if len(grupos[c]) == 3)
    exemplo_falho = mascarados[0]["correlation_id"] if mascarados else None
    relato.texto(f"Trace de uma operação sem falha (`{exemplo_limpo[:12]}…`)", "\n".join(desenhar(montar_arvore(grupos[exemplo_limpo]))), codigo=True)
    if exemplo_falho:
        relato.texto(
            f"Trace de uma operação com falha mascarada (`{exemplo_falho[:12]}…`)",
            "\n".join(desenhar(montar_arvore(grupos[exemplo_falho]))),
            codigo=True,
        )
        span_do_erro = next(s for s in grupos[exemplo_falho] if s["service"] == "balcao" and s["span_kind"] == "client" and s["outcome"] == "server_error")
        relato.texto("Linha de log do balcão para a tentativa que falhou", json.dumps(span_do_erro, ensure_ascii=False, indent=2), codigo=True)
        relato.texto(
            "Leitura",
            "O cliente recebeu 200 nessa operação e não tem como saber que houve um erro. O log do balcão sozinho mostra "
            "uma tentativa com 500, mas não diz qual requisição externa estava sendo atendida, nem o que aconteceu dentro do "
            "acervo. Com o mesmo `correlation_id` nos três arquivos, a árvore se monta sozinha: o span de servidor do balcão "
            "é a raiz, cada tentativa é um filho, e o span do acervo pendura na tentativa pelo `parent_span_id`. A tentativa 1 "
            "e a tentativa 2 têm o mesmo `message_id`, porque são a mesma mensagem lógica. Por isso o acervo-a e o acervo-b "
            "aparecem com a mesma mensagem, que é como se detecta uma entrega duplicada. Numa leitura, isso é inofensivo. Numa "
            "escrita, seria o sinal de que o acervo precisa deduplicar por esse identificador (o problema da AP5).",
        )

    relato.verificar("todas as requisições com sucesso no cliente", f"{total}", resumo["sucessos"], resumo["sucessos"] == total)
    relato.verificar("toda operação reconstruída nos três processos", f"{total}", completos, completos == total)
    relato.verificar("nenhum span órfão", "0", len(sem_pai), not sem_pai)
    relato.verificar("cadeia de causalidade íntegra", f"{len(spans_do_acervo)}", causas_corretas, causas_corretas == len(spans_do_acervo))
    relato.verificar("houve erros internos para observar", "> 0", len(erros_internos), len(erros_internos) > 0)
    relato.verificar("todo erro interno foi mascarado pelo failover", f"{len(erros_internos)}", len(mascarados), len(mascarados) == len(erros_internos))
    relato.verificar("cada erro mascarado aparece como mensagem repetida", f"{len(mascarados)}", len(repetidas), len(repetidas) == len(mascarados))

    relato.dados = {
        "resumo": resumo,
        "completos": completos,
        "orfaos": len(sem_pai),
        "erros_internos": len(erros_internos),
        "mascarados": len(mascarados),
        "repetidas": len(repetidas),
    }
    relato.conclusao = (
        f"{relato.veredito()} O cliente viu {resumo['sucessos']} de {total} sucessos. Por dentro, o acervo-a falhou "
        f"{len(erros_internos)} vezes em {sum(1 for s in spans_do_acervo if s['instance'] == 'acervo-a')} atendimentos, e todas "
        "essas falhas foram reconstruídas e ligadas à requisição que as causou. Sem propagação de identificadores, a "
        "taxa de erro de 0% no cliente seria a única informação disponível, e a réplica com defeito passaria despercebida "
        "até a outra réplica cair também."
    )
    relato.salvar()
    return relato


if __name__ == "__main__":
    executar()
    gerar()
