import time

from starlette.middleware.base import BaseHTTPMiddleware

from observabilidade.contexto import ContextoDeRequisicao, cabecalho_correlacao, cabecalho_span
from observabilidade.registro import agora_ms


def desfecho_do_status(status):
    if status < 400:
        return "success"
    if status < 500:
        return "client_error"
    return "server_error"


class SpanDeServidor(BaseHTTPMiddleware):
    def __init__(self, app, registrador, ignorar=()):
        super().__init__(app)
        self.registrador = registrador
        self.ignorar = set(ignorar)

    async def dispatch(self, requisicao, chamar_proximo):
        if requisicao.url.path in self.ignorar:
            return await chamar_proximo(requisicao)

        contexto = ContextoDeRequisicao.dos_cabecalhos(requisicao.headers)
        requisicao.state.contexto = contexto
        requisicao.state.detalhes = {}
        inicio_ms = agora_ms()
        inicio = time.perf_counter()

        try:
            resposta = await chamar_proximo(requisicao)
        except Exception as erro:
            self.escrever(requisicao, contexto, inicio_ms, inicio, 500, "exception", type(erro).__name__)
            raise

        resposta.headers[cabecalho_correlacao] = contexto.correlation_id
        resposta.headers[cabecalho_span] = contexto.span_id
        self.escrever(requisicao, contexto, inicio_ms, inicio, resposta.status_code, desfecho_do_status(resposta.status_code))
        return resposta

    def escrever(self, requisicao, contexto, inicio_ms, inicio, status, desfecho, erro=None):
        rota = requisicao.scope.get("route")
        self.registrador.registrar(
            operation=getattr(rota, "name", None) or requisicao.url.path,
            outcome=desfecho,
            level="ERROR" if status >= 500 else "INFO",
            correlation_id=contexto.correlation_id,
            message_id=contexto.message_id,
            causation_id=contexto.causation_id,
            span_id=contexto.span_id,
            parent_span_id=contexto.parent_span_id,
            span_kind="server",
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
            start_ms=inicio_ms,
            method=requisicao.method,
            path=requisicao.url.path,
            status=status,
            error=erro,
            **getattr(requisicao.state, "detalhes", {}),
        )
