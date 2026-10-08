import threading

from cliente.resiliencia import chamar_com_retry
from experimentos.comum import Servidor, ident, inicio_do_evento, pico_por_janela

codigo = "E07"
titulo = "Tempestade de retries: imediato contra backoff com jitter"
hipotese = (
    "Com 20 clientes começando juntos e 60% de falha, retries imediatos concentram as tentativas em poucos "
    "milissegundos. Backoff exponencial com jitter espalha as mesmas tentativas no tempo e reduz o pico de "
    "requisições que o servidor recebe."
)
falha_injetada = "prob_falha=0.6; 20 clientes disparados ao mesmo tempo; até 4 tentativas por cliente"
classificacao = (
    "Não é falha de um componente: é efeito emergente da política de retry (amplificação de carga). Num "
    "servidor no limite, esse pico vira falha de temporização ou omissão para todos os clientes."
)

clientes = 20
probabilidade = 0.6
tentativas = 4
janela = 0.1


def duracao_da_rajada(eventos):
    inicios = [inicio_do_evento(evento) for evento in eventos]
    return (max(inicios) - min(inicios)) * 1000


def rodada(servidor, coletor, nome, base, jitter):
    largada = threading.Barrier(clientes)
    resultados = [None] * clientes

    def cliente(indice):
        largada.wait()
        resultados[indice] = chamar_com_retry(
            "GET",
            f"{servidor.url}/experimento/instavel",
            tentativas=tentativas,
            timeout=2.0,
            base=base,
            jitter=jitter,
            correlacao=f"{nome}-{indice:02d}",
            params={"prob_falha": probabilidade},
        )

    linhas = [threading.Thread(target=cliente, args=(indice,)) for indice in range(clientes)]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join(30)

    for resultado in resultados:
        coletor.anotar(codigo, nome, resultado, detalhar=False)

    eventos = [evento for evento in servidor.eventos("/experimento/instavel") if evento["correlacao"].startswith(nome)]
    return resultados, eventos


def executar(coletor):
    with Servidor(ident(codigo, "servidor"), semente="ap5-e07") as servidor:
        imediato, eventos_imediato = rodada(servidor, coletor, "imediato", base=0.0, jitter=0.0)
        espalhado, eventos_espalhado = rodada(servidor, coletor, "backoff", base=0.2, jitter=0.1)

        pico_imediato = pico_por_janela(eventos_imediato, janela)
        pico_espalhado = pico_por_janela(eventos_espalhado, janela)
        rajada_imediato = duracao_da_rajada(eventos_imediato)
        rajada_espalhado = duracao_da_rajada(eventos_espalhado)
        sucesso_imediato = sum(resultado.ok for resultado in imediato)
        sucesso_espalhado = sum(resultado.ok for resultado in espalhado)

        coletor.registrar(
            codigo,
            "requisições no servidor por chamada lógica (imediato)",
            "> 1",
            f"{len(eventos_imediato) / clientes:.2f}",
            f"{clientes} chamadas viraram {len(eventos_imediato)} requisições. Toda política de retry amplifica carga "
            "durante a falha.",
            sucesso=len(eventos_imediato) > clientes,
        )
        coletor.registrar(
            codigo,
            f"pico de requisições em {janela * 1000:.0f} ms (imediato)",
            f"> {clientes}",
            f"{pico_imediato} de {len(eventos_imediato)}",
            f"O pico passou do número de clientes: as repetições caíram na mesma janela de {janela * 1000:.0f} ms do "
            "primeiro disparo, somando-se a ele em vez de esperar o servidor se recuperar.",
            sucesso=pico_imediato > clientes,
        )
        coletor.registrar(
            codigo,
            f"pico de requisições em {janela * 1000:.0f} ms (backoff + jitter)",
            f"<= {clientes} e < {pico_imediato}",
            f"{pico_espalhado} de {len(eventos_espalhado)}",
            "O primeiro disparo continua simultâneo, mas nenhuma repetição se soma a ele: as ondas seguintes chegam "
            "cada vez mais tarde e desalinhadas pelo jitter.",
            sucesso=pico_espalhado <= clientes and pico_espalhado < pico_imediato,
        )
        coletor.registrar(
            codigo,
            "duração da rajada (primeira à última requisição)",
            "imediato < backoff",
            f"{rajada_imediato:.0f} ms imediato, {rajada_espalhado:.0f} ms backoff",
            "A mesma quantidade de trabalho foi comprimida em poucas centenas de milissegundos no retry imediato e "
            "espalhada por mais de um segundo com backoff.",
            sucesso=rajada_imediato < rajada_espalhado,
        )
        coletor.registrar(
            codigo,
            "taxa de sucesso nas duas políticas",
            "semelhante",
            f"{sucesso_imediato}/{clientes} imediato, {sucesso_espalhado}/{clientes} backoff",
            "Com falha aleatória independente, o número de tentativas decide o sucesso, não o intervalo. O backoff "
            "não piora o resultado: só muda quando a carga chega.",
            sucesso=abs(sucesso_imediato - sucesso_espalhado) <= 4,
        )

        duracao_imediato = max(resultado.duracao_total_ms for resultado in imediato)
        duracao_espalhado = max(resultado.duracao_total_ms for resultado in espalhado)
        coletor.concluir(
            codigo,
            f"imediato: {len(eventos_imediato)} requisições em {rajada_imediato:.0f} ms, pico de {pico_imediato} em "
            f"{janela * 1000:.0f} ms, "
            f"{sucesso_imediato}/{clientes} sucessos, pior cliente em {duracao_imediato:.0f} ms; backoff: "
            f"{len(eventos_espalhado)} requisições em {rajada_espalhado:.0f} ms, pico de {pico_espalhado}, "
            f"{sucesso_espalhado}/{clientes} "
            f"sucessos, pior cliente em {duracao_espalhado:.0f} ms.",
            f"Backoff com jitter reduziu o pico de {pico_imediato} para {pico_espalhado} requisições por "
            f"{janela * 1000:.0f} ms com sucesso equivalente, ao custo de recuperação mais lenta. Retry imediato em "
            "massa é o mecanismo pelo qual uma falha parcial vira sobrecarga.",
        )
