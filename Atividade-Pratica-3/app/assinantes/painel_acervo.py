import argparse
import threading
import time
from collections import Counter

from app import config, conexao, topicos
from app.envelope import Envelope, EnvelopeInvalido, RastreadorDeSequencia
from app.registro import Registrador

FILTROS = (topicos.FILTRO_DE_EMPRESTIMOS, topicos.FILTRO_DE_DEVOLUCOES)


class PainelDeAcervo:
    def __init__(
        self,
        identificador=config.PAINEL_ACERVO,
        *,
        qos=config.QOS_PADRAO,
        atraso_de_processamento=0.0,
        sessao_persistente=False,
        registrador=None,
        filtros=FILTROS,
    ):
        self.identificador = identificador
        self.qos = qos
        self.atraso_de_processamento = atraso_de_processamento
        self.sessao_persistente = sessao_persistente
        self.filtros = tuple(filtros)
        self.registrador = registrador or Registrador(identificador, "assinante")
        self.conectado = threading.Event()
        self.rastreador = RastreadorDeSequencia()
        self.em_circulacao = Counter()
        self.recebidas = 0
        self.repetidas = 0
        self.lacunas = 0
        self.invalidas = 0
        self.atraso_maximo_ms = 0.0
        self.limite_de_mensagens = None
        self.alvo_atingido = threading.Event()
        self.cliente = conexao.criar_cliente(identificador)
        self.cliente.on_connect = self._ao_conectar
        self.cliente.on_disconnect = self._ao_desconectar
        self.cliente.on_message = self._ao_receber

    def _ao_conectar(self, cliente, userdata, flags, reason_code, propriedades):
        if reason_code.is_failure:
            self.registrador.evento("conexao-recusada", detalhe=str(reason_code))
            return
        self.conectado.set()
        for filtro in self.filtros:
            cliente.subscribe(filtro, qos=self.qos)
        self.registrador.evento(
            "conectado",
            filtros=list(self.filtros),
            qos=self.qos,
            sessao_retomada=bool(flags.session_present),
        )

    def _ao_desconectar(self, cliente, userdata, flags, reason_code, propriedades):
        self.conectado.clear()
        self.registrador.evento("desconectado", detalhe=str(reason_code))

    def _ao_receber(self, cliente, userdata, mensagem):
        if self.atraso_de_processamento > 0:
            time.sleep(self.atraso_de_processamento)

        try:
            envelope = Envelope.de_bytes(mensagem.payload)
        except EnvelopeInvalido as erro:
            self.invalidas += 1
            self.registrador.evento(
                "envelope-invalido",
                topico=mensagem.topic,
                detalhe=str(erro),
            )
            return

        self.recebidas += 1
        atraso = envelope.atraso_ms()
        if atraso is not None:
            self.atraso_maximo_ms = max(self.atraso_maximo_ms, atraso)

        classificacao, lacuna = self.rastreador.classificar(
            envelope.producer_id, envelope.sequence
        )
        if classificacao == "repetida":
            self.repetidas += 1
        if classificacao == "lacuna":
            self.lacunas += lacuna

        evento = topicos.evento_de(mensagem.topic)
        titulo = envelope.data.get("titulo", "?")
        if evento == topicos.EMPRESTIMO:
            self.em_circulacao[titulo] += 1
        elif evento == topicos.DEVOLUCAO:
            self.em_circulacao[titulo] = max(0, self.em_circulacao[titulo] - 1)

        self.registrador.evento(
            "recebido",
            topico=mensagem.topic,
            tipo=evento,
            qos=mensagem.qos,
            sequence=envelope.sequence,
            message_id=envelope.message_id,
            producer_id=envelope.producer_id,
            dup=bool(mensagem.dup),
            retain=bool(mensagem.retain),
            classificacao=classificacao,
            lacuna=lacuna,
            atraso_ms=atraso,
        )

        if self.limite_de_mensagens and self.recebidas >= self.limite_de_mensagens:
            self.alvo_atingido.set()

    def iniciar(self):
        conexao.conectar(
            self.cliente,
            sessao_persistente=self.sessao_persistente,
            registrador=self.registrador,
        )
        self.cliente.loop_start()
        self.conectado.wait(10.0)

    def resumo(self):
        faltantes = {
            produtor: self.rastreador.faltantes(produtor)
            for produtor in sorted(self.rastreador.recebidas_por_produtor)
        }
        return {
            "recebidas": self.recebidas,
            "repetidas": self.repetidas,
            "lacunas": self.lacunas,
            "invalidas": self.invalidas,
            "atraso_maximo_ms": self.atraso_maximo_ms,
            "ultima_sequencia": dict(self.rastreador.ultima_por_produtor),
            "sequencias_faltantes": faltantes,
            "em_circulacao": dict(self.em_circulacao),
        }

    def encerrar(self):
        self.registrador.evento("resumo", **self.resumo())
        self.cliente.loop_stop()
        self.cliente.disconnect()
        self.registrador.fechar()


def analisar_argumentos(argumentos=None):
    analisador = argparse.ArgumentParser(
        prog="python -m app.assinantes.painel_acervo",
        description="Painel que observa todas as movimentações do acervo (fan-out).",
    )
    analisador.add_argument("--id", dest="identificador", default=config.PAINEL_ACERVO)
    analisador.add_argument("--qos", type=int, choices=(0, 1, 2), default=config.QOS_PADRAO)
    analisador.add_argument("--lento", type=float, default=0.0)
    analisador.add_argument("--sessao-persistente", action="store_true")
    analisador.add_argument("--ate-mensagens", type=int, default=0)
    analisador.add_argument("--duracao", type=float, default=0.0)
    analisador.add_argument("--filtro", action="append", default=None)
    analisador.add_argument("--silencioso", action="store_true")
    return analisador.parse_args(argumentos)


def main(argumentos=None):
    opcoes = analisar_argumentos(argumentos)
    parada = conexao.Encerramento()
    registrador = Registrador(
        opcoes.identificador, "assinante", silencioso=opcoes.silencioso
    )
    painel = PainelDeAcervo(
        opcoes.identificador,
        qos=opcoes.qos,
        atraso_de_processamento=opcoes.lento,
        sessao_persistente=opcoes.sessao_persistente,
        registrador=registrador,
        filtros=opcoes.filtro or FILTROS,
    )
    painel.limite_de_mensagens = opcoes.ate_mensagens or None
    painel.iniciar()
    try:
        parada.aguardar_com_alvo(
            alvo=painel.alvo_atingido if opcoes.ate_mensagens else None,
            limite=opcoes.duracao or None,
        )
    except KeyboardInterrupt:
        pass
    finally:
        painel.encerrar()


if __name__ == "__main__":
    main()
