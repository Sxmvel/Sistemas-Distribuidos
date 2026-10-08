import threading
import time

from cliente.resiliencia import chamar_com_retry, requisitar
from experimentos.comum import Servidor, ident

codigo = "E04"
titulo = "Indisponibilidade e crash do servidor"
hipotese = (
    "Sem processo escutando na porta, o cliente não recebe status HTTP: a falha é de transporte. Se o servidor "
    "volta dentro da janela de retry, o backoff transforma a indisponibilidade em sucesso. Se o processo morre "
    "no meio de uma requisição, o cliente vê a conexão interrompida, sem saber se o efeito foi aplicado."
)
falha_injetada = "servidor encerrado; servidor religado durante o backoff; processo morto (kill) no meio de uma requisição de 3 s"
classificacao = (
    "Crash do processo. No laboratório parece fail-stop porque o sistema operacional ainda responde com recusa "
    "(RST); se o host inteiro caísse, a mesma falha apareceria como timeout."
)


def executar(coletor):
    servidor = Servidor(ident(codigo, "servidor"))
    servidor.iniciar()
    try:
        saude = f"{servidor.url}/v1/saude"
        no_ar = coletor.anotar(codigo, "servidor no ar", requisitar("GET", saude, timeout=0.5))
        coletor.registrar(codigo, "linha de base com o servidor no ar", "sucesso", no_ar.categoria, "Estado inicial.")

        servidor.parar()

        curto = coletor.anotar(codigo, "servidor fora, timeout 0,5 s", requisitar("GET", saude, timeout=0.5))
        coletor.registrar(
            codigo,
            "servidor fora com timeout de 0,5 s",
            "timeout-de-conexao",
            curto.categoria,
            f"Falhou em {curto.ultima.duracao_ms:.0f} ms como timeout de conexão. No Windows, a recusa em localhost "
            "só é reportada depois de ~2 s de novas tentativas de SYN; com timeout menor que isso, a recusa se "
            "disfarça de timeout.",
        )

        longo = coletor.anotar(
            codigo, "servidor fora, timeout de conexão 3 s", requisitar("GET", saude, timeout=(3.0, 0.5))
        )
        coletor.registrar(
            codigo,
            "servidor fora com timeout de conexão de 3 s",
            "conexao-recusada",
            longo.categoria,
            f"Com prazo suficiente, a causa real aparece em {longo.ultima.duracao_ms:.0f} ms: WinError 10061, "
            "recusa ativa. A mesma falha recebeu dois nomes diferentes conforme o timeout escolhido.",
        )

        religar = threading.Timer(1.0, servidor.iniciar)
        religar.start()
        recuperacao = coletor.anotar(
            codigo,
            "retry enquanto o servidor é religado",
            chamar_com_retry("GET", saude, tentativas=6, timeout=0.5, base=0.2, jitter=0.1),
        )
        religar.join()
        coletor.registrar(
            codigo,
            "retry com backoff durante a reinicialização",
            "sucesso após falhas",
            f"{recuperacao.categoria} na tentativa {len(recuperacao.tentativas)}",
            f"{len(recuperacao.tentativas) - 1} tentativa(s) sem conexão antes de o servidor voltar e a última com "
            f"200, em {recuperacao.duracao_total_ms / 1000:.1f} s no total. Aqui o retry melhorou o resultado: a "
            "indisponibilidade era temporária.",
            sucesso=recuperacao.ok and len(recuperacao.tentativas) > 1,
        )

        resultado_da_queda = {}

        def chamar_lenta():
            resultado_da_queda["valor"] = requisitar(
                "GET", f"{servidor.url}/experimento/instavel", timeout=5.0, params={"atraso_ms": 3000}
            )

        linha = threading.Thread(target=chamar_lenta)
        linha.start()
        time.sleep(0.7)
        servidor.matar()
        linha.join(10)
        queda = coletor.anotar(codigo, "kill no meio de uma requisição de 3 s", resultado_da_queda["valor"])

        coletor.registrar(
            codigo,
            "processo morto no meio da requisição",
            "conexao-interrompida",
            queda.categoria,
            f"O cliente percebeu em {queda.ultima.duracao_ms:.0f} ms, bem antes do timeout de 5 s, porque o sistema "
            "operacional fechou a conexão do processo morto.",
        )
        coletor.registrar(
            codigo,
            "servidor não registrou a requisição interrompida",
            0,
            len(servidor.eventos(correlacao=queda.correlacao)),
            "O log do servidor não tem a linha de conclusão: o processo morreu antes. Numa escrita, o cliente não "
            "saberia se o efeito chegou a ser aplicado.",
        )

        coletor.concluir(
            codigo,
            f"fora do ar: timeout-de-conexao em {curto.ultima.duracao_ms:.0f} ms (timeout 0,5 s) e conexao-recusada "
            f"em {longo.ultima.duracao_ms:.0f} ms (timeout 3 s); retry durante a reinicialização: sucesso na "
            f"tentativa {len(recuperacao.tentativas)}; kill no meio: conexao-interrompida em "
            f"{queda.ultima.duracao_ms:.0f} ms, sem registro no servidor.",
            "Indisponibilidade é distinguível de erro de aplicação (não há status HTTP), mas a forma como aparece "
            "depende do timeout. O retry com backoff resolveu porque a queda era temporária; o crash no meio da "
            "requisição deixa o efeito em aberto.",
        )
    finally:
        servidor.matar()
