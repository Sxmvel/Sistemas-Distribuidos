import secrets
import uuid
from dataclasses import dataclass

cabecalho_correlacao = "X-Correlation-ID"
cabecalho_mensagem = "X-Message-ID"
cabecalho_causa = "X-Causation-ID"
cabecalho_span_pai = "X-Parent-Span-ID"
cabecalho_span = "X-Span-ID"


def novo_correlation_id():
    return uuid.uuid4().hex


def novo_message_id():
    return uuid.uuid4().hex[:16]


def novo_span_id():
    return secrets.token_hex(8)


@dataclass(frozen=True)
class ContextoDeRequisicao:
    correlation_id: str
    message_id: str
    causation_id: str | None
    span_id: str
    parent_span_id: str | None

    @classmethod
    def dos_cabecalhos(cls, cabecalhos):
        return cls(
            correlation_id=cabecalhos.get(cabecalho_correlacao) or novo_correlation_id(),
            message_id=cabecalhos.get(cabecalho_mensagem) or novo_message_id(),
            causation_id=cabecalhos.get(cabecalho_causa),
            span_id=novo_span_id(),
            parent_span_id=cabecalhos.get(cabecalho_span_pai),
        )

    def cabecalhos_para_dependencia(self, message_id, span_da_chamada):
        return {
            cabecalho_correlacao: self.correlation_id,
            cabecalho_mensagem: message_id,
            cabecalho_causa: self.message_id,
            cabecalho_span_pai: span_da_chamada,
        }
