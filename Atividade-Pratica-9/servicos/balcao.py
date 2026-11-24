import asyncio
import itertools
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from observabilidade.contexto import novo_message_id, novo_span_id
from observabilidade.middleware import SpanDeServidor, desfecho_do_status
from observabilidade.registro import RegistradorEstruturado, agora_ms
from servicos.configuracao import ConfiguracaoBalcao
from servicos.relogio import ativar_relogio_fino
from servicos.respostas import problema

status_da_falha = {
    "timeout_conexao": 504,
    "timeout_leitura": 504,
    "conexao_recusada": 503,
    "conexao_interrompida": 503,
    "transporte": 503,
}


def classificar_falha(erro):
    if isinstance(erro, httpx.ConnectTimeout):
        return "timeout_conexao"
    if isinstance(erro, httpx.TimeoutException):
        return "timeout_leitura"
    if isinstance(erro, httpx.ConnectError):
        return "conexao_recusada"
    if isinstance(erro, (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError)):
        return "conexao_interrompida"
    return "transporte"


@dataclass
class Replica:
    url: str
    suspeita_ate: float = 0.0

    def disponivel(self, agora):
        return agora >= self.suspeita_ate


@dataclass
class ResultadoDaDependencia:
    status: int | None
    corpo: object
    tentativas: int
    replica: str | None
    falhas: list = field(default_factory=list)

    @property
    def ok(self):
        return self.status is not None and self.status < 400


def criar_app(configuracao=None, transporte=None):
    configuracao = configuracao or ConfiguracaoBalcao.do_ambiente()
    registrador = RegistradorEstruturado("balcao", configuracao.instancia, configuracao.arquivo_de_log)
    replicas = [Replica(url.rstrip("/")) for url in configuracao.replicas]
    rodizio = itertools.count()

    @asynccontextmanager
    async def ciclo_de_vida(app):
        app.state.cliente = httpx.AsyncClient(
            transport=transporte,
            timeout=httpx.Timeout(configuracao.timeout_ms / 1000, connect=configuracao.timeout_conexao_ms / 1000),
            limits=httpx.Limits(max_connections=256, max_keepalive_connections=128),
        )
        registrador.registrar(
            operation="iniciar",
            outcome="success",
            replicas=[replica.url for replica in replicas],
            timeout_ms=configuracao.timeout_ms,
            timeout_conexao_ms=configuracao.timeout_conexao_ms,
            quarentena_s=configuracao.quarentena_s,
            relogio_fino=ativar_relogio_fino(),
        )
        yield
        await app.state.cliente.aclose()
        registrador.registrar(operation="encerrar", outcome="success")
        registrador.fechar()

    app = FastAPI(title=f"Balcão ({configuracao.instancia})", version="1.0", lifespan=ciclo_de_vida)
    app.state.configuracao = configuracao
    app.state.replicas = replicas
    app.state.registrador = registrador
    app.add_middleware(SpanDeServidor, registrador=registrador)

    def ordem_das_replicas():
        agora = time.monotonic()
        inicio = next(rodizio) % len(replicas)
        giradas = replicas[inicio:] + replicas[:inicio]
        return [r for r in giradas if r.disponivel(agora)] + [r for r in giradas if not r.disponivel(agora)]

    async def chamar_acervo(requisicao, caminho, operacao):
        contexto = requisicao.state.contexto
        message_id = novo_message_id()
        falhas = []

        for numero, replica in enumerate(ordem_das_replicas(), start=1):
            span_id = novo_span_id()
            inicio_ms = agora_ms()
            inicio = time.perf_counter()
            status, resposta, falha = None, None, None
            try:
                resposta = await app.state.cliente.get(
                    replica.url + caminho,
                    headers=contexto.cabecalhos_para_dependencia(message_id, span_id),
                )
                status = resposta.status_code
            except httpx.HTTPError as erro:
                falha = classificar_falha(erro)

            quarentena = None
            if falha is not None:
                replica.suspeita_ate = time.monotonic() + configuracao.quarentena_s
                quarentena = configuracao.quarentena_s
                desfecho = "transport_error"
            else:
                desfecho = desfecho_do_status(status)

            registrador.registrar(
                operation=operacao,
                outcome=desfecho,
                level="WARNING" if falha or status >= 500 else "INFO",
                correlation_id=contexto.correlation_id,
                message_id=message_id,
                causation_id=contexto.message_id,
                span_id=span_id,
                parent_span_id=contexto.span_id,
                span_kind="client",
                duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
                start_ms=inicio_ms,
                attempt=numero,
                replica=replica.url,
                status=status,
                error=falha,
                quarantine_s=quarentena,
            )

            if falha is None and status < 500:
                return ResultadoDaDependencia(status, resposta.json(), numero, replica.url, falhas)
            falhas.append(falha or f"http_{status}")

        return ResultadoDaDependencia(None, None, len(falhas), None, falhas)

    def falha_da_dependencia(resultado):
        ultima = resultado.falhas[-1] if resultado.falhas else "sem_replica"
        status = 502 if ultima.startswith("http_") else status_da_falha.get(ultima, 503)
        resposta = problema(
            status,
            "Dependência indisponível",
            f"nenhuma réplica do acervo respondeu ({', '.join(resultado.falhas)})",
            configuracao.instancia,
            falhas=resultado.falhas,
        )
        if status == 503:
            resposta.headers["Retry-After"] = "1"
        return resposta

    @app.get("/v1/saude", name="saude")
    async def saude():
        agora = time.monotonic()
        return {
            "status": "ok",
            "instancia": configuracao.instancia,
            "replicas": [{"url": r.url, "em_quarentena": not r.disponivel(agora)} for r in replicas],
        }

    @app.get("/v1/livros/{livro_id}", name="consultar_livro")
    async def consultar_livro(livro_id: int, requisicao: Request):
        resultado = await chamar_acervo(requisicao, f"/v1/livros/{livro_id}", "acervo.consultar_livro")
        requisicao.state.detalhes.update(attempts=resultado.tentativas, dependency_calls=1)
        if resultado.status is None:
            return falha_da_dependencia(resultado)
        if resultado.status >= 400:
            return JSONResponse(resultado.corpo, status_code=resultado.status, media_type="application/problem+json")
        return resultado.corpo

    @app.get("/v1/vitrine", name="montar_vitrine")
    async def montar_vitrine(requisicao: Request, quantidade: int = Query(5, ge=1, le=12)):
        resultados = await asyncio.gather(
            *(chamar_acervo(requisicao, f"/v1/livros/{indice}", "acervo.consultar_livro") for indice in range(1, quantidade + 1))
        )
        requisicao.state.detalhes.update(
            attempts=sum(r.tentativas for r in resultados),
            dependency_calls=quantidade,
        )
        falhos = [r for r in resultados if not r.ok]
        if falhos:
            return falha_da_dependencia(falhos[0])
        return {"quantidade": quantidade, "livros": [r.corpo for r in resultados]}

    return app
