from cliente.resiliencia import requisitar
from experimentos.comum import Servidor, ident, percentil

codigo = "E01"
titulo = "Cenário de referência sem falha"
hipotese = (
    "Sem falha injetada, todas as chamadas terminam com sucesso, o servidor registra exatamente as "
    "requisições que o cliente enviou e a latência fica muito abaixo do timeout de 500 ms."
)
falha_injetada = "nenhuma"
classificacao = (
    "Sem falha. Linha de base que sustenta o modelo síncrono assumido pelo cliente: atraso limitado e "
    "conhecido, bem abaixo do timeout."
)

timeout = 0.5
chamadas_na_rota_instavel = 30
chamadas_no_recurso = 10


def executar(coletor):
    with Servidor(ident(codigo, "servidor")) as servidor:
        livro = servidor.cadastrar_livro("Dom Casmurro (E01)", exemplares=2)
        resultados = []

        for _ in range(chamadas_na_rota_instavel):
            resultado = requisitar("GET", f"{servidor.url}/experimento/instavel", timeout=timeout)
            resultados.append(coletor.anotar(codigo, "GET /experimento/instavel", resultado, detalhar=False))

        for _ in range(chamadas_no_recurso):
            resultado = requisitar("GET", f"{servidor.url}/v1/livros/{livro['id']}", timeout=timeout)
            resultados.append(coletor.anotar(codigo, f"GET /v1/livros/{livro['id']}", resultado, detalhar=False))

        total = len(resultados)
        sucessos = sum(resultado.ok for resultado in resultados)
        duracoes = [resultado.ultima.duracao_ms for resultado in resultados]
        p50, p95, p99 = percentil(duracoes, 0.5), percentil(duracoes, 0.95), percentil(duracoes, 0.99)
        no_servidor = [
            evento for evento in servidor.eventos()
            if evento["caminho"] in ("/experimento/instavel", f"/v1/livros/{livro['id']}") and evento["metodo"] == "GET"
        ]
        duracao_no_servidor = [evento["duracao_ms"] for evento in no_servidor]

        coletor.registrar(
            codigo,
            "chamadas concluídas com 200",
            f"{total}/{total}",
            f"{sucessos}/{total}",
            "Nenhuma falha sem injeção: qualquer erro nos cenários seguintes é atribuível ao que foi injetado.",
        )
        coletor.registrar(
            codigo,
            "p95 da latência abaixo do timeout",
            "< 500 ms",
            f"{p95} ms",
            f"p50={p50} ms, p95={p95} ms, p99={p99} ms. O timeout de 500 ms fica "
            f"{500 / max(p95, 0.1):.0f}x acima do p95: há folga suficiente para não haver falso fracasso.",
            sucesso=p95 < 500,
        )
        coletor.registrar(
            codigo,
            "requisições registradas no servidor",
            total,
            len(no_servidor),
            "Cliente e servidor contam o mesmo número de requisições: nenhuma omissão no canal.",
        )
        coletor.registrar(
            codigo,
            "tempo no servidor menor que o tempo no cliente",
            True,
            percentil(duracao_no_servidor, 0.5) <= p50,
            f"Mediana no servidor {percentil(duracao_no_servidor, 0.5)} ms contra {p50} ms no cliente. A diferença "
            "é conexão TCP, serialização e escalonamento: custo que existe mesmo sem falha.",
        )

        coletor.concluir(
            codigo,
            f"{sucessos}/{total} chamadas com 200; p50={p50} ms, p95={p95} ms, p99={p99} ms; "
            f"servidor registrou {len(no_servidor)} requisições, mediana interna de "
            f"{percentil(duracao_no_servidor, 0.5)} ms.",
            f"O timeout de 500 ms está cerca de {500 / max(p95, 0.1):.0f}x acima do p95 normal. Por isso, um "
            "timeout nos cenários seguintes indica a falha injetada, e não flutuação comum de latência.",
        )
