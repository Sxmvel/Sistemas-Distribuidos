import random
import time

from app import config
from app.erros import RecursoNaoEncontrado

sorteio = random.Random(config.semente_das_falhas)


def exigir_laboratorio() -> None:
    if not config.laboratorio_ativo:
        raise RecursoNaoEncontrado("Rota de laboratório desativada neste ambiente.")


def atrasar_escrita() -> None:
    if config.atraso_na_escrita > 0:
        time.sleep(config.atraso_na_escrita)


def deve_falhar(probabilidade: float) -> bool:
    return sorteio.random() < probabilidade
