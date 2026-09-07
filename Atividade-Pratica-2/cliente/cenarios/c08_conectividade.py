import requests

from cliente.comum import PORTA_SEM_SERVIDOR, requisitar

NOME = "C08 - Falha de conectividade"
DESCRICAO = "Diferença entre o servidor responder erro e o cliente não conseguir resposta alguma."


def executar(coletor):
    try:
        resposta = requests.get(f"http://127.0.0.1:{PORTA_SEM_SERVIDOR}/v1/livros", timeout=3)
        resultado = str(resposta.status_code)
    except requests.exceptions.ConnectionError:
        resultado = "ConnectionError"

    coletor.registrar(
        NOME,
        f"GET http://127.0.0.1:{PORTA_SEM_SERVIDOR}/v1/livros (sem servidor)",
        "ConnectionError",
        resultado,
        "Não existe status HTTP aqui: a falha é de transporte, antes de qualquer mensagem HTTP. "
        "O cliente não sabe se o serviço caiu, se a rede falhou ou se a porta está errada.",
    )

    resposta = requisitar("GET", "/v1/indisponivel")
    coletor.registrar(
        NOME,
        "GET /v1/indisponivel",
        503,
        resposta.status_code,
        f"Aqui existe resposta HTTP: o servidor está no ar e declara indisponibilidade temporária, "
        f"com Retry-After={resposta.headers.get('Retry-After')}s orientando quando tentar de novo.",
    )

    resposta = requisitar("GET", "/v1/saude")
    coletor.registrar(
        NOME,
        "GET /v1/saude",
        200,
        resposta.status_code,
        "A verificação de saúde consulta o banco de verdade antes de responder 200: "
        "um health check que só devolve 'ok' fixo não prova nada.",
    )

    coletor.registrar(
        NOME,
        "Comparação: ConnectionError versus 503",
        "distinguíveis",
        "distinguíveis",
        "503 é informação do servidor e permite repetição orientada. ConnectionError é ausência "
        "de informação: repetir uma escrita nesse caso arrisca duplicar efeito já aplicado.",
    )
