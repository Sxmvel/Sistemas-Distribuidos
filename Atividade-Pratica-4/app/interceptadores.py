import threading
import time
import uuid
from collections import Counter, namedtuple

import grpc

from app import config, erros
from app.dominio import ErroDeDominio


def nome_curto(metodo):
    return metodo.rsplit("/", 1)[-1]


def valor_do_metadado(metadados, chave):
    for item in metadados or ():
        if item[0] == chave:
            return item[1]
    return None


class Metricas:
    def __init__(self):
        self._trava = threading.Lock()
        self.por_metodo = {}
        self.por_status = Counter()

    def anotar(self, metodo, status, latencia_ms):
        with self._trava:
            amostras = self.por_metodo.setdefault(metodo, [])
            amostras.append(latencia_ms)
            self.por_status[status] += 1

    def resumo(self):
        with self._trava:
            return {
                metodo: {
                    "chamadas": len(amostras),
                    "media_ms": round(sum(amostras) / len(amostras), 1),
                    "maior_ms": round(max(amostras), 1),
                }
                for metodo, amostras in sorted(self.por_metodo.items())
            }, dict(self.por_status)


class InterceptadorDoServidor(grpc.ServerInterceptor):
    def __init__(self, registrador, metricas=None):
        self.registrador = registrador
        self.metricas = metricas or Metricas()

    def intercept_service(self, continuation, handler_call_details):
        manipulador = continuation(handler_call_details)
        if manipulador is None:
            return None
        metodo = nome_curto(handler_call_details.method)
        correlacao = valor_do_metadado(
            handler_call_details.invocation_metadata, config.CHAVE_DE_CORRELACAO
        )

        if manipulador.unary_unary is not None:
            return grpc.unary_unary_rpc_method_handler(
                self._unario(manipulador.unary_unary, metodo, correlacao),
                request_deserializer=manipulador.request_deserializer,
                response_serializer=manipulador.response_serializer,
            )
        if manipulador.unary_stream is not None:
            return grpc.unary_stream_rpc_method_handler(
                self._fluxo(manipulador.unary_stream, metodo, correlacao),
                request_deserializer=manipulador.request_deserializer,
                response_serializer=manipulador.response_serializer,
            )
        return manipulador

    def _concluir(self, metodo, status, inicio, correlacao, **campos):
        latencia = (time.perf_counter() - inicio) * 1000
        self.metricas.anotar(metodo, status, latencia)
        self.registrador.evento(
            "chamada-concluida",
            metodo=metodo,
            status=status,
            latencia_ms=round(latencia, 1),
            correlacao=correlacao,
            **campos,
        )

    def _tratar(self, erro, metodo, contexto, inicio, correlacao):
        if isinstance(erro, erros.ChamadaAbandonada):
            self._concluir(
                metodo,
                "ABANDONADA_PELO_CLIENTE",
                inicio,
                correlacao,
                detalhe=str(erro),
                processados=erro.processados,
                total=erro.total,
            )
            return
        status = erros.status_de(erro)
        detalhe = erros.detalhe_de(erro)
        self._concluir(metodo, status.name, inicio, correlacao, detalhe=detalhe)
        campo = getattr(erro, "campo", None)
        if campo:
            contexto.set_trailing_metadata(
                ((config.CHAVE_DE_CORRELACAO, correlacao or ""), ("x-campo", campo))
            )
        contexto.abort(status, detalhe)

    def _unario(self, comportamento, metodo, correlacao):
        def rotina(pedido, contexto):
            inicio = time.perf_counter()
            self.registrador.evento(
                "chamada-recebida",
                metodo=metodo,
                correlacao=correlacao,
                prazo_restante_s=arredondar(contexto.time_remaining()),
            )
            try:
                resposta = comportamento(pedido, contexto)
            except (ErroDeDominio, erros.ChamadaAbandonada) as erro:
                self._tratar(erro, metodo, contexto, inicio, correlacao)
                return None
            self._concluir(metodo, grpc.StatusCode.OK.name, inicio, correlacao)
            return resposta

        return rotina

    def _fluxo(self, comportamento, metodo, correlacao):
        def rotina(pedido, contexto):
            inicio = time.perf_counter()
            self.registrador.evento(
                "chamada-recebida", metodo=metodo, correlacao=correlacao
            )
            enviados = 0
            try:
                for resposta in comportamento(pedido, contexto):
                    enviados += 1
                    yield resposta
            except (ErroDeDominio, erros.ChamadaAbandonada) as erro:
                self._tratar(erro, metodo, contexto, inicio, correlacao)
                return
            self._concluir(
                metodo, grpc.StatusCode.OK.name, inicio, correlacao, enviados=enviados
            )

        return rotina


def arredondar(valor):
    return None if valor is None else round(valor, 3)


class DetalhesDaChamada(
    namedtuple(
        "DetalhesDaChamada",
        ("method", "timeout", "metadata", "credentials", "wait_for_ready", "compression"),
    ),
    grpc.ClientCallDetails,
):
    pass


class InterceptadorDoCliente(
    grpc.UnaryUnaryClientInterceptor, grpc.UnaryStreamClientInterceptor
):
    def __init__(self, registrador, origem, metricas=None):
        self.registrador = registrador
        self.origem = origem
        self.metricas = metricas or Metricas()

    def _com_correlacao(self, detalhes_da_chamada):
        metadados = list(detalhes_da_chamada.metadata or ())
        correlacao = valor_do_metadado(metadados, config.CHAVE_DE_CORRELACAO)
        if correlacao is None:
            correlacao = f"{self.origem}-{uuid.uuid4().hex[:8]}"
            metadados.append((config.CHAVE_DE_CORRELACAO, correlacao))
        detalhes = DetalhesDaChamada(
            detalhes_da_chamada.method,
            detalhes_da_chamada.timeout,
            metadados,
            detalhes_da_chamada.credentials,
            getattr(detalhes_da_chamada, "wait_for_ready", None),
            getattr(detalhes_da_chamada, "compression", None),
        )
        return detalhes, correlacao

    def _anotar(self, metodo, chamada, inicio, correlacao):
        latencia = (time.perf_counter() - inicio) * 1000
        status = chamada.code().name if chamada.code() is not None else "SEM_STATUS"
        self.metricas.anotar(metodo, status, latencia)
        self.registrador.evento(
            "resposta-recebida",
            metodo=metodo,
            status=status,
            latencia_ms=round(latencia, 1),
            correlacao=correlacao,
        )

    def intercept_unary_unary(self, continuation, detalhes_da_chamada, pedido):
        detalhes, correlacao = self._com_correlacao(detalhes_da_chamada)
        metodo = nome_curto(detalhes.method)
        inicio = time.perf_counter()
        chamada = continuation(detalhes, pedido)
        self._anotar(metodo, chamada, inicio, correlacao)
        return chamada

    def intercept_unary_stream(self, continuation, detalhes_da_chamada, pedido):
        detalhes, correlacao = self._com_correlacao(detalhes_da_chamada)
        metodo = nome_curto(detalhes.method)
        inicio = time.perf_counter()
        chamada = continuation(detalhes, pedido)
        self.registrador.evento(
            "fluxo-aberto", metodo=metodo, correlacao=correlacao, latencia_ms=round(
                (time.perf_counter() - inicio) * 1000, 1
            )
        )
        return chamada
