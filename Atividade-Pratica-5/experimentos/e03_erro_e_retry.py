from cliente.resiliencia import chamar_com_retry, requisitar
from experimentos.comum import Servidor, ident

codigo = "E03"
titulo = "Erro de aplicação probabilístico, sem e com retry"
hipotese = (
    "Com prob_falha=0,5, cerca de metade das chamadas sem retry falha com 503. Com até 4 tentativas e "
    "backoff exponencial, a taxa de sucesso sobe para perto de 1 - 0,5^4 = 94%, ao custo de mais requisições "
    "no servidor e de latência maior nas chamadas que precisaram repetir."
)
falha_injetada = "prob_falha=0.5 com semente fixa no servidor; prob_falha=1.5 para o caso de entrada inválida"
classificacao = (
    "Omissão transitória do serviço, sinalizada explicitamente como erro de aplicação (503). O processo e o "
    "canal estão corretos; é o único caso em que o cliente recebe informação positiva sobre o que aconteceu."
)

chamadas = 20
probabilidade = 0.5
tentativas = 4
base = 0.2
jitter = 0.1


def taxa(resultados):
    return sum(resultado.ok for resultado in resultados) / len(resultados)


def executar(coletor):
    with Servidor(ident(codigo, "servidor"), semente="ap5-e03") as servidor:
        destino = f"{servidor.url}/experimento/instavel"
        parametros = {"prob_falha": probabilidade}

        sem_retry = [
            coletor.anotar(codigo, "sem retry", requisitar("GET", destino, timeout=0.5, params=parametros), detalhar=False)
            for _ in range(chamadas)
        ]
        com_retry = [
            coletor.anotar(
                codigo,
                "com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s)",
                chamar_com_retry("GET", destino, tentativas=tentativas, timeout=0.5, base=base, jitter=jitter, params=parametros),
            )
            for _ in range(chamadas)
        ]

        taxa_sem, taxa_com = taxa(sem_retry), taxa(com_retry)
        tentativas_com = sum(len(resultado.tentativas) for resultado in com_retry)
        categorias_sem = {resultado.categoria for resultado in sem_retry if not resultado.ok}

        coletor.registrar(
            codigo,
            "taxa de sucesso sem retry",
            "entre 20% e 80%",
            f"{taxa_sem:.0%}",
            "Cada chamada é uma única aposta contra a falha injetada.",
            sucesso=0.2 <= taxa_sem <= 0.8,
        )
        coletor.registrar(
            codigo,
            "tipo de erro observado sem retry",
            "erro-de-aplicacao",
            ", ".join(sorted(categorias_sem)) or "nenhum",
            "Existe resposta HTTP 503 com corpo problem+json: o servidor está vivo e declara a falha. Não há "
            "ambiguidade sobre o efeito, ao contrário do timeout.",
        )
        coletor.registrar(
            codigo,
            "taxa de sucesso com retry",
            ">= 85%",
            f"{taxa_com:.0%}",
            f"Subiu de {taxa_sem:.0%} para {taxa_com:.0%}. Retry funciona aqui porque a falha é transitória e "
            "independente entre tentativas, e a operação é uma leitura idempotente.",
            sucesso=taxa_com >= 0.85 and taxa_com > taxa_sem,
        )
        coletor.registrar(
            codigo,
            "tentativas por chamada respeitam o limite",
            f"<= {tentativas}",
            max(len(resultado.tentativas) for resultado in com_retry),
            "O retry é limitado: uma falha persistente não vira laço infinito.",
            sucesso=all(len(resultado.tentativas) <= tentativas for resultado in com_retry),
        )

        esperas_ok = all(
            base * 2**(item.numero - 1) <= item.espera_s <= base * 2**(item.numero - 1) + jitter
            for resultado in com_retry
            for item in resultado.tentativas[:-1]
        )
        coletor.registrar(
            codigo,
            "esperas seguem backoff exponencial com jitter",
            True,
            esperas_ok,
            "A n-ésima espera fica em [0,2 x 2^(n-1), 0,2 x 2^(n-1) + 0,1] s, como no retry.py do enunciado.",
            sucesso=esperas_ok,
        )

        no_servidor = [
            evento for evento in servidor.eventos("/experimento/instavel")
            if evento["consulta"] == f"prob_falha={probabilidade}"
        ]
        coletor.registrar(
            codigo,
            "amplificação de carga no servidor",
            f"{chamadas + tentativas_com} requisições",
            f"{len(no_servidor)} requisições",
            f"{chamadas} chamadas lógicas com retry geraram {tentativas_com} requisições "
            f"({tentativas_com / chamadas:.2f} por chamada). O preço da disponibilidade é carga extra.",
            sucesso=len(no_servidor) == chamadas + tentativas_com,
        )

        invalida = coletor.anotar(
            codigo,
            "prob_falha=1.5 com retry",
            chamar_com_retry("GET", destino, tentativas=tentativas, timeout=0.5, params={"prob_falha": 1.5}),
        )
        coletor.registrar(
            codigo,
            "erro do cliente não é repetido",
            "1 tentativa (422)",
            f"{len(invalida.tentativas)} tentativa ({invalida.status})",
            "422 é determinístico: repetir a mesma entrada inválida daria o mesmo erro. Só falhas transitórias "
            "entram na política de retry.",
        )

        duracao_com = sorted(resultado.duracao_total_ms for resultado in com_retry)
        coletor.concluir(
            codigo,
            f"sem retry: {taxa_sem:.0%} de sucesso, erros 503; com retry: {taxa_com:.0%} de sucesso, "
            f"{tentativas_com} requisições para {chamadas} chamadas, pior chamada em {duracao_com[-1]:.0f} ms; "
            f"422 com {len(invalida.tentativas)} tentativa.",
            f"Retry melhorou o resultado de {taxa_sem:.0%} para {taxa_com:.0%} porque a falha é transitória e a "
            "leitura é idempotente. O custo apareceu como carga extra no servidor e latência maior nas chamadas "
            "azaradas.",
        )
