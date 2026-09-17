import argparse
import signal
from concurrent import futures

import grpc

from app import config
from app.interceptadores import InterceptadorDoServidor, Metricas
from app.registro import Registrador
from app.repositorio import Repositorio
from app.servico import ServicoDeEmprestimos
from contratos import emprestimos_pb2_grpc as pb2_grpc

OPCOES_DO_CANAL = [
    ("grpc.max_send_message_length", config.TAMANHO_MAXIMO_DA_MENSAGEM),
    ("grpc.max_receive_message_length", config.TAMANHO_MAXIMO_DA_MENSAGEM),
]


def criar_servidor(
    porta=0,
    workers=config.WORKERS_PADRAO,
    repositorio=None,
    registrador=None,
    custo_por_codigo=None,
    metricas=None,
    atraso_na_escrita=0.0,
):
    registrador = registrador or Registrador("servidor", "servidor", silencioso=True)
    metricas = metricas or Metricas()
    servidor = grpc.server(
        futures.ThreadPoolExecutor(max_workers=workers),
        interceptors=(InterceptadorDoServidor(registrador, metricas),),
        options=OPCOES_DO_CANAL,
        maximum_concurrent_rpcs=config.CHAMADAS_CONCORRENTES_MAXIMAS,
    )
    servico = ServicoDeEmprestimos(
        repositorio or Repositorio(),
        custo_por_codigo=custo_por_codigo,
        atraso_na_escrita=atraso_na_escrita,
    )
    pb2_grpc.add_EmprestimosServicer_to_server(servico, servidor)
    porta_efetiva = servidor.add_insecure_port(f"127.0.0.1:{porta}")
    if porta_efetiva == 0:
        raise SystemExit(f"não foi possível abrir a porta {porta}")
    return servidor, servico, porta_efetiva, registrador, metricas


def argumentos(entrada=None):
    analisador = argparse.ArgumentParser(description="Servidor gRPC de empréstimos")
    analisador.add_argument("--porta", type=int, default=config.SERVIDOR_PORTA)
    analisador.add_argument("--workers", type=int, default=config.WORKERS_PADRAO)
    analisador.add_argument("--id", default="servidor")
    analisador.add_argument("--semear", type=int, default=0)
    analisador.add_argument(
        "--custo-por-codigo", type=float, default=config.CUSTO_POR_CODIGO_NA_MULTA
    )
    analisador.add_argument("--atraso-na-escrita", type=float, default=0.0)
    analisador.add_argument("--silencioso", action="store_true")
    return analisador.parse_args(entrada)


def main(entrada=None):
    opcoes = argumentos(entrada)
    registrador = Registrador(opcoes.id, "servidor", silencioso=opcoes.silencioso)
    repositorio = Repositorio()
    if opcoes.semear:
        repositorio.semear(opcoes.semear)

    servidor, _, porta, _, metricas = criar_servidor(
        porta=opcoes.porta,
        workers=opcoes.workers,
        repositorio=repositorio,
        registrador=registrador,
        custo_por_codigo=opcoes.custo_por_codigo,
        atraso_na_escrita=opcoes.atraso_na_escrita,
    )
    servidor.start()
    registrador.evento(
        "servidor-no-ar",
        porta=porta,
        workers=opcoes.workers,
        custo_por_codigo=opcoes.custo_por_codigo,
        atraso_na_escrita=opcoes.atraso_na_escrita,
        semeados=opcoes.semear,
    )
    print(f"servidor gRPC em 127.0.0.1:{porta} (workers={opcoes.workers})", flush=True)

    parada = signal.SIGBREAK if hasattr(signal, "SIGBREAK") else signal.SIGTERM

    def encerrar(*_):
        servidor.stop(2).wait()

    signal.signal(signal.SIGINT, encerrar)
    try:
        signal.signal(parada, encerrar)
    except (OSError, ValueError):
        pass

    try:
        servidor.wait_for_termination()
    except KeyboardInterrupt:
        servidor.stop(2).wait()
    finally:
        por_metodo, por_status = metricas.resumo()
        registrador.evento("resumo", por_metodo=por_metodo, por_status=por_status)
        registrador.fechar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
