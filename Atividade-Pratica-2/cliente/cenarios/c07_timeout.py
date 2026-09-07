import requests

from cliente.comum import requisitar

NOME = "C07 - Timeout"
DESCRICAO = "A mesma rota lenta observada sob três limites de tempo diferentes no cliente."

ESPERA_DO_SERVIDOR = 2.0


def medir(coletor, limite):
    requisicao = f"GET /v1/lento?segundos={ESPERA_DO_SERVIDOR} com timeout={limite}s"
    try:
        resposta = requisitar("GET", "/v1/lento", timeout=limite, params={"segundos": ESPERA_DO_SERVIDOR})
        resultado = str(resposta.status_code)
    except requests.exceptions.Timeout:
        resultado = "Timeout"

    esperado = "Timeout" if limite < ESPERA_DO_SERVIDOR else "200"
    analise = (
        "O servidor processou normalmente; quem desistiu foi o cliente. A operação pode ter "
        "sido concluída do outro lado, e o cliente não tem como saber."
        if resultado == "Timeout"
        else "Dentro do limite, a resposta chega íntegra: o timeout é uma decisão do cliente "
        "sobre quanto tempo aceita esperar, não uma propriedade do servidor."
    )
    coletor.registrar(NOME, requisicao, esperado, resultado, analise)


def executar(coletor):
    for limite in (0.5, 1.0, 3.0):
        medir(coletor, limite)

    coletor.registrar(
        NOME,
        "Timeout definido em todas as chamadas do cliente",
        "sim",
        "sim",
        "cliente/comum.py define TIMEOUT=3.0 e o repassa em toda requisição. Sem timeout, "
        "a biblioteca requests espera indefinidamente e um serviço lento derruba o chamador.",
    )
