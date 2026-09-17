import grpc

from app.dominio import ErroDeDominio

STATUS_POR_CATEGORIA = {
    "entrada_invalida": grpc.StatusCode.INVALID_ARGUMENT,
    "nao_encontrado": grpc.StatusCode.NOT_FOUND,
    "precondicao_falhou": grpc.StatusCode.FAILED_PRECONDITION,
    "ja_existe": grpc.StatusCode.ALREADY_EXISTS,
}

CATEGORIA_POR_STATUS = {
    status.name: categoria for categoria, status in STATUS_POR_CATEGORIA.items()
}

REPETIVEIS = frozenset({grpc.StatusCode.UNAVAILABLE.name})
NUNCA_REPETIR = frozenset(
    {
        grpc.StatusCode.INVALID_ARGUMENT.name,
        grpc.StatusCode.NOT_FOUND.name,
        grpc.StatusCode.FAILED_PRECONDITION.name,
        grpc.StatusCode.ALREADY_EXISTS.name,
        grpc.StatusCode.PERMISSION_DENIED.name,
    }
)
AMBIGUOS = frozenset(
    {grpc.StatusCode.DEADLINE_EXCEEDED.name, grpc.StatusCode.CANCELLED.name}
)


class ChamadaAbandonada(Exception):
    def __init__(self, processados, total):
        super().__init__(f"cliente desistiu após {processados} de {total} itens")
        self.processados = processados
        self.total = total


def status_de(erro):
    if isinstance(erro, ErroDeDominio):
        return STATUS_POR_CATEGORIA[erro.categoria]
    return grpc.StatusCode.INTERNAL


def detalhe_de(erro):
    if isinstance(erro, ErroDeDominio):
        return f"{erro.campo}: {erro.mensagem}" if erro.campo else erro.mensagem
    return "erro interno do servidor"


def politica_de_retry(status):
    nome = status.name if hasattr(status, "name") else str(status)
    if nome in REPETIVEIS:
        return "repetir com backoff"
    if nome in NUNCA_REPETIR:
        return "corrigir a chamada, nunca repetir"
    if nome in AMBIGUOS:
        return "repetir apenas com chave de idempotência"
    return "investigar"
