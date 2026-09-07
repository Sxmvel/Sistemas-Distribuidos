import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.config import VERSAO_DO_ESQUEMA

CAMPOS_OBRIGATORIOS = (
    "message_id",
    "producer_id",
    "sequence",
    "schema_version",
    "timestamp",
    "data",
)

SEQUENCIA_DO_TESTAMENTO = 0


class EnvelopeInvalido(Exception):
    pass


def agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Envelope:
    message_id: str
    producer_id: str
    sequence: int
    schema_version: int
    timestamp: str
    data: dict

    @classmethod
    def novo(cls, producer_id, sequence, data, schema_version=VERSAO_DO_ESQUEMA):
        return cls(
            message_id=uuid.uuid4().hex,
            producer_id=producer_id,
            sequence=sequence,
            schema_version=schema_version,
            timestamp=agora_iso(),
            data=dict(data),
        )

    def para_bytes(self):
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def de_bytes(cls, bruto):
        try:
            conteudo = json.loads(bruto.decode("utf-8"))
        except UnicodeDecodeError as erro:
            raise EnvelopeInvalido(f"payload não está em UTF-8: {erro}") from erro
        except json.JSONDecodeError as erro:
            raise EnvelopeInvalido(f"payload não é JSON válido: {erro}") from erro

        if not isinstance(conteudo, dict):
            raise EnvelopeInvalido("o envelope precisa ser um objeto JSON")

        ausentes = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in conteudo]
        if ausentes:
            raise EnvelopeInvalido("campos ausentes no envelope: " + ", ".join(ausentes))

        sequencia = conteudo["sequence"]
        if not isinstance(sequencia, int) or isinstance(sequencia, bool) or sequencia < 0:
            raise EnvelopeInvalido(f"sequence precisa ser inteiro não negativo: {sequencia!r}")

        versao = conteudo["schema_version"]
        if not isinstance(versao, int) or versao > VERSAO_DO_ESQUEMA:
            raise EnvelopeInvalido(
                f"schema_version {versao!r} não é suportado por este consumidor "
                f"(máximo conhecido: {VERSAO_DO_ESQUEMA})"
            )

        if not isinstance(conteudo["data"], dict):
            raise EnvelopeInvalido("data precisa ser um objeto JSON")

        return cls(
            message_id=str(conteudo["message_id"]),
            producer_id=str(conteudo["producer_id"]),
            sequence=sequencia,
            schema_version=versao,
            timestamp=str(conteudo["timestamp"]),
            data=conteudo["data"],
        )

    @property
    def e_testamento(self):
        return self.sequence == SEQUENCIA_DO_TESTAMENTO

    def atraso_ms(self, recebido_em=None):
        try:
            produzido = datetime.fromisoformat(self.timestamp)
        except ValueError:
            return None
        if produzido.tzinfo is None:
            produzido = produzido.replace(tzinfo=timezone.utc)
        instante = recebido_em or datetime.now(timezone.utc)
        return round((instante - produzido).total_seconds() * 1000, 2)


class Sequenciador:
    def __init__(self, inicio=0):
        self._valor = inicio

    def proximo(self):
        self._valor += 1
        return self._valor

    @property
    def atual(self):
        return self._valor


class RastreadorDeSequencia:
    def __init__(self):
        self.ultima_por_produtor = {}
        self.recebidas_por_produtor = {}

    def classificar(self, producer_id, sequence):
        vistas = self.recebidas_por_produtor.setdefault(producer_id, set())
        anterior = self.ultima_por_produtor.get(producer_id)

        if sequence in vistas:
            return "repetida", 0

        vistas.add(sequence)

        if anterior is None:
            self.ultima_por_produtor[producer_id] = sequence
            return "primeira", 0

        if sequence == anterior + 1:
            self.ultima_por_produtor[producer_id] = sequence
            return "em-ordem", 0

        if sequence > anterior + 1:
            lacuna = sequence - anterior - 1
            self.ultima_por_produtor[producer_id] = sequence
            return "lacuna", lacuna

        return "fora-de-ordem", 0

    def faltantes(self, producer_id):
        vistas = self.recebidas_por_produtor.get(producer_id, set())
        if not vistas:
            return []
        return sorted(set(range(1, max(vistas) + 1)) - vistas)
