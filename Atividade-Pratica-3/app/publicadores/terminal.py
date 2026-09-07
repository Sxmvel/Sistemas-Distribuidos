import argparse
import random
import threading
import time

import paho.mqtt.client as mqtt

from app import acervo, config, conexao, topicos
from app.envelope import SEQUENCIA_DO_TESTAMENTO, Envelope, Sequenciador
from app.registro import Registrador

LIMITE_DE_CONFIRMACAO = 30.0
LIMITE_DE_CONNACK = 10.0


class Terminal:
    def __init__(
        self,
        unidade,
        terminal,
        *,
        qos=config.QOS_PADRAO,
        keepalive=config.KEEPALIVE_PADRAO,
        semente=None,
        reenviar_a_cada=0,
        registrador=None,
    ):
        self.unidade = unidade
        self.terminal = terminal
        self.qos = qos
        self.keepalive = keepalive
        self.reenviar_a_cada = reenviar_a_cada
        self.sorteio = random.Random(semente)
        self.sequenciador = Sequenciador()
        self.registrador = registrador or Registrador(terminal, "publicador")
        self.conectado = threading.Event()
        self.topico_de_status = topicos.de_status(unidade, terminal)
        self.cliente = conexao.criar_cliente(
            terminal,
            testamento=self._testamento(),
            keepalive=keepalive,
        )
        self.cliente.on_connect = self._ao_conectar
        self.cliente.on_disconnect = self._ao_desconectar

    def _envelope_de_status(self, estado, motivo, sequencia=None):
        return Envelope.novo(
            producer_id=self.terminal,
            sequence=self.sequenciador.atual if sequencia is None else sequencia,
            data={
                "estado": estado,
                "motivo": motivo,
                "unidade": self.unidade,
            },
        )

    def _testamento(self):
        envelope = self._envelope_de_status(
            "offline",
            "desconexao-anormal",
            sequencia=SEQUENCIA_DO_TESTAMENTO,
        )
        return (self.topico_de_status, envelope.para_bytes(), 1, True)

    def _ao_conectar(self, cliente, userdata, flags, reason_code, propriedades):
        if reason_code.is_failure:
            self.registrador.evento("conexao-recusada", detalhe=str(reason_code))
            return
        self.conectado.set()
        self.registrador.evento(
            "conectado",
            broker=f"{config.BROKER_HOST}:{config.BROKER_PORTA}",
            sessao_retomada=bool(flags.session_present),
        )
        self.anunciar("online", "terminal-em-operacao")

    def _ao_desconectar(self, cliente, userdata, flags, reason_code, propriedades):
        self.conectado.clear()
        self.registrador.evento("desconectado", detalhe=str(reason_code))

    def iniciar(self):
        conexao.conectar(
            self.cliente,
            keepalive=self.keepalive,
            registrador=self.registrador,
        )
        self.cliente.loop_start()
        if not self.conectado.wait(LIMITE_DE_CONNACK):
            raise conexao.BrokerIndisponivel("conexão aceita mas CONNACK não chegou")

    def anunciar(self, estado, motivo):
        envelope = self._envelope_de_status(estado, motivo)
        info = self.cliente.publish(
            self.topico_de_status,
            envelope.para_bytes(),
            qos=1,
            retain=True,
        )
        self.registrador.evento(
            "status-publicado",
            topico=self.topico_de_status,
            estado=estado,
            motivo=motivo,
            message_id=envelope.message_id,
            retain=True,
            qos=1,
            aceito=info.rc == mqtt.MQTT_ERR_SUCCESS,
        )

    def _proxima_movimentacao(self):
        livro = self.sorteio.choice(acervo.LIVROS)
        leitor = self.sorteio.choice(acervo.LEITORES)
        if self.sorteio.random() < 0.6:
            return topicos.EMPRESTIMO, {
                "acao": topicos.EMPRESTIMO,
                "isbn": livro["isbn"],
                "titulo": livro["titulo"],
                "leitor": leitor,
                "prazo_dias": acervo.PRAZO_EM_DIAS,
                "unidade": self.unidade,
            }
        atraso = self.sorteio.choice([0, 0, 0, 1, 3, 7])
        return topicos.DEVOLUCAO, {
            "acao": topicos.DEVOLUCAO,
            "isbn": livro["isbn"],
            "titulo": livro["titulo"],
            "leitor": leitor,
            "dias_de_atraso": atraso,
            "unidade": self.unidade,
        }

    def publicar(self, envelope, evento, reenvio=False):
        topico = topicos.montar(self.unidade, self.terminal, evento)
        info = self.cliente.publish(topico, envelope.para_bytes(), qos=self.qos)
        aceito = info.rc == mqtt.MQTT_ERR_SUCCESS

        confirmado = None
        if aceito and self.qos > 0:
            try:
                info.wait_for_publish(LIMITE_DE_CONFIRMACAO)
                confirmado = info.is_published()
            except (RuntimeError, ValueError):
                confirmado = False

        self.registrador.evento(
            "reenviado" if reenvio else "publicado",
            topico=topico,
            tipo=evento,
            qos=self.qos,
            sequence=envelope.sequence,
            message_id=envelope.message_id,
            aceito=aceito,
            confirmado=confirmado,
            codigo=int(info.rc),
        )
        return aceito

    def executar(self, mensagens, intervalo, parada=None):
        for indice in range(1, mensagens + 1):
            if parada is not None and parada.solicitado.is_set():
                break
            evento, dados = self._proxima_movimentacao()
            envelope = Envelope.novo(
                producer_id=self.terminal,
                sequence=self.sequenciador.proximo(),
                data=dados,
            )
            self.publicar(envelope, evento)
            if self.reenviar_a_cada and indice % self.reenviar_a_cada == 0:
                self.publicar(envelope, evento, reenvio=True)
            if intervalo > 0:
                time.sleep(intervalo)

    def encerrar(self, motivo="encerramento-programado"):
        if self.conectado.is_set():
            self.anunciar("offline", motivo)
            time.sleep(0.2)
        self.cliente.loop_stop()
        self.cliente.disconnect()
        self.registrador.evento("encerrado", motivo=motivo)
        self.registrador.fechar()


def analisar_argumentos(argumentos=None):
    analisador = argparse.ArgumentParser(
        prog="python -m app.publicadores.terminal",
        description="Terminal de autoatendimento que publica movimentações da biblioteca.",
    )
    analisador.add_argument("--unidade", default="central")
    analisador.add_argument("--terminal", default="term-01")
    analisador.add_argument("--qos", type=int, choices=(0, 1, 2), default=config.QOS_PADRAO)
    analisador.add_argument("--mensagens", type=int, default=60)
    analisador.add_argument("--intervalo", type=float, default=0.2)
    analisador.add_argument("--keepalive", type=int, default=config.KEEPALIVE_PADRAO)
    analisador.add_argument("--semente", type=int, default=None)
    analisador.add_argument("--reenviar-a-cada", type=int, default=0)
    analisador.add_argument("--manter-vivo", action="store_true")
    analisador.add_argument("--silencioso", action="store_true")
    return analisador.parse_args(argumentos)


def main(argumentos=None):
    opcoes = analisar_argumentos(argumentos)
    parada = conexao.Encerramento()
    registrador = Registrador(opcoes.terminal, "publicador", silencioso=opcoes.silencioso)
    terminal = Terminal(
        opcoes.unidade,
        opcoes.terminal,
        qos=opcoes.qos,
        keepalive=opcoes.keepalive,
        semente=opcoes.semente,
        reenviar_a_cada=opcoes.reenviar_a_cada,
        registrador=registrador,
    )
    terminal.iniciar()
    try:
        terminal.executar(opcoes.mensagens, opcoes.intervalo, parada=parada)
        if opcoes.manter_vivo:
            parada.aguardar()
    except KeyboardInterrupt:
        pass
    finally:
        terminal.encerrar()


if __name__ == "__main__":
    main()
