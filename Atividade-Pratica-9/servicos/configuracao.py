import os
from dataclasses import dataclass, field


def texto(nome, padrao=None):
    valor = os.getenv(nome)
    return valor if valor not in (None, "") else padrao


def numero(nome, padrao):
    valor = texto(nome)
    return float(valor) if valor is not None else padrao


@dataclass(frozen=True)
class ConfiguracaoAcervo:
    instancia: str = "acervo-a"
    trabalhadores: int = 32
    tempo_servico_ms: float = 10.0
    prob_lentidao: float = 0.0
    atraso_lento_ms: float = 0.0
    prob_erro: float = 0.0
    semente: int | None = None
    arquivo_de_log: str | None = None

    @classmethod
    def do_ambiente(cls):
        semente = texto("ACERVO_SEMENTE")
        return cls(
            instancia=texto("ACERVO_INSTANCIA", cls.instancia),
            trabalhadores=int(numero("ACERVO_TRABALHADORES", cls.trabalhadores)),
            tempo_servico_ms=numero("ACERVO_TEMPO_SERVICO_MS", cls.tempo_servico_ms),
            prob_lentidao=numero("ACERVO_PROB_LENTIDAO", cls.prob_lentidao),
            atraso_lento_ms=numero("ACERVO_ATRASO_LENTO_MS", cls.atraso_lento_ms),
            prob_erro=numero("ACERVO_PROB_ERRO", cls.prob_erro),
            semente=int(semente) if semente is not None else None,
            arquivo_de_log=texto("AP9_LOG"),
        )


@dataclass(frozen=True)
class ConfiguracaoBalcao:
    instancia: str = "balcao-1"
    replicas: tuple = field(default=("http://127.0.0.1:8201",))
    timeout_ms: float = 1000.0
    timeout_conexao_ms: float = 150.0
    quarentena_s: float = 2.0
    arquivo_de_log: str | None = None

    @classmethod
    def do_ambiente(cls):
        replicas = texto("BALCAO_REPLICAS")
        return cls(
            instancia=texto("BALCAO_INSTANCIA", cls.instancia),
            replicas=tuple(item.strip() for item in replicas.split(",")) if replicas else cls.replicas,
            timeout_ms=numero("BALCAO_TIMEOUT_MS", cls.timeout_ms),
            timeout_conexao_ms=numero("BALCAO_TIMEOUT_CONEXAO_MS", cls.timeout_conexao_ms),
            quarentena_s=numero("BALCAO_QUARENTENA_S", cls.quarentena_s),
            arquivo_de_log=texto("AP9_LOG"),
        )
