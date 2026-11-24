import asyncio
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from observabilidade.middleware import SpanDeServidor
from observabilidade.registro import RegistradorEstruturado
from servicos import dados
from servicos.configuracao import ConfiguracaoAcervo
from servicos.relogio import ativar_relogio_fino
from servicos.respostas import problema


class FilaDeAtendimento:
    def __init__(self, trabalhadores):
        self.trabalhadores = trabalhadores
        self.semaforo = asyncio.Semaphore(trabalhadores)
        self.na_fila = 0
        self.em_atendimento = 0
        self.atendidas = 0
        self.pico_da_fila = 0

    def retrato(self):
        return {
            "trabalhadores": self.trabalhadores,
            "na_fila": self.na_fila,
            "em_atendimento": self.em_atendimento,
            "atendidas": self.atendidas,
            "pico_da_fila": self.pico_da_fila,
        }


def criar_app(configuracao=None):
    configuracao = configuracao or ConfiguracaoAcervo.do_ambiente()
    registrador = RegistradorEstruturado("acervo", configuracao.instancia, configuracao.arquivo_de_log)
    sorteio = random.Random(configuracao.semente)
    fila = FilaDeAtendimento(configuracao.trabalhadores)

    @asynccontextmanager
    async def ciclo_de_vida(app):
        registrador.registrar(
            operation="iniciar",
            outcome="success",
            trabalhadores=configuracao.trabalhadores,
            tempo_servico_ms=configuracao.tempo_servico_ms,
            prob_lentidao=configuracao.prob_lentidao,
            atraso_lento_ms=configuracao.atraso_lento_ms,
            prob_erro=configuracao.prob_erro,
            relogio_fino=ativar_relogio_fino(),
        )
        yield
        registrador.registrar(operation="encerrar", outcome="success")
        registrador.fechar()

    app = FastAPI(title=f"Acervo ({configuracao.instancia})", version="1.0", lifespan=ciclo_de_vida)
    app.state.configuracao = configuracao
    app.state.fila = fila
    app.state.registrador = registrador
    app.add_middleware(SpanDeServidor, registrador=registrador, ignorar={"/v1/metricas"})

    async def atender(requisicao):
        chegada = time.perf_counter()
        fila.na_fila += 1
        fila.pico_da_fila = max(fila.pico_da_fila, fila.na_fila)
        async with fila.semaforo:
            fila.na_fila -= 1
            fila.em_atendimento += 1
            inicio = time.perf_counter()
            lento = sorteio.random() < configuracao.prob_lentidao
            falhou = sorteio.random() < configuracao.prob_erro
            atraso_ms = configuracao.tempo_servico_ms + (configuracao.atraso_lento_ms if lento else 0)
            try:
                await asyncio.sleep(atraso_ms / 1000)
            finally:
                fila.em_atendimento -= 1
                fila.atendidas += 1
        requisicao.state.detalhes.update(
            espera_ms=round((inicio - chegada) * 1000, 2),
            servico_ms=round((time.perf_counter() - inicio) * 1000, 2),
            lento=True if lento else None,
            falha_injetada=True if falhou else None,
        )
        return falhou

    @app.get("/v1/saude", name="saude")
    async def saude():
        return {"status": "ok", "instancia": configuracao.instancia}

    @app.get("/v1/metricas", name="metricas")
    async def metricas():
        return {"instancia": configuracao.instancia, **fila.retrato()}

    @app.get("/v1/livros/{livro_id}", name="consultar_livro")
    async def consultar_livro(livro_id: int, requisicao: Request):
        falhou = await atender(requisicao)
        if falhou:
            return problema(500, "Falha interna", "falha injetada pelo laboratório", configuracao.instancia)
        livro = dados.livros.get(livro_id)
        if livro is None:
            return problema(404, "Livro não encontrado", f"não existe livro {livro_id}", configuracao.instancia)
        return {**livro, "instancia": configuracao.instancia}

    return app
