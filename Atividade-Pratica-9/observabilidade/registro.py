import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

campos_em_ordem = (
    "timestamp",
    "level",
    "service",
    "instance",
    "correlation_id",
    "message_id",
    "causation_id",
    "span_id",
    "parent_span_id",
    "span_kind",
    "operation",
    "duration_ms",
    "outcome",
)


def agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def agora_ms():
    return round(time.time() * 1000, 3)


class RegistradorEstruturado:
    def __init__(self, servico, instancia, caminho=None):
        self.servico = servico
        self.instancia = instancia
        self.registrador = logging.getLogger(f"ap9.{servico}.{instancia}.{id(self)}")
        self.registrador.setLevel(logging.INFO)
        self.registrador.propagate = False
        if caminho:
            Path(caminho).parent.mkdir(parents=True, exist_ok=True)
            destino = logging.FileHandler(caminho, encoding="utf-8")
            destino.setFormatter(logging.Formatter("%(message)s"))
            self.registrador.addHandler(destino)
        else:
            self.registrador.addHandler(logging.NullHandler())

    def registrar(self, operation, outcome, level="INFO", **campos):
        base = {
            "timestamp": agora_iso(),
            "level": level,
            "service": self.servico,
            "instance": self.instancia,
            "operation": operation,
            "outcome": outcome,
            **campos,
        }
        evento = {chave: base[chave] for chave in campos_em_ordem if base.get(chave) is not None}
        evento.update({chave: valor for chave, valor in base.items() if chave not in evento and valor is not None})
        self.registrador.log(logging.getLevelName(level), json.dumps(evento, ensure_ascii=False))
        return evento

    def fechar(self):
        for destino in list(self.registrador.handlers):
            destino.close()
            self.registrador.removeHandler(destino)
