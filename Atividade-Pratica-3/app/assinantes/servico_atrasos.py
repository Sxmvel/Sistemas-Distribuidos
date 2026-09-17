import argparse
import threading

from app import config, conexao, topicos
from app.envelope import Envelope, EnvelopeInvalido, RastreadorDeSequencia
from app.persistencia import RepositorioDeAtrasos
from app.registro import Registrador


class ServicoDeAtrasos:
    def __init__(
        self,
        identificador=config.SERVICO_ATRASOS,
        *,
        qos=config.QOS_PADRAO,
        deduplicar=True,
        sessao_persistente=True,
        reiniciar_banco=False,
        caminho_do_banco=None,
        registrador=None,
        filtros=(topicos.FILTRO_DE_TUDO,),
    ):
        self.identificador = identificador
        self.qos = qos
        self.deduplicar = deduplicar
        self.sessao_persistente = sessao_persistente
        self.filtros = tuple(filtros)
        self.registrador = registrador or Registrador(identificador, "assinante")
        self.repositorio = RepositorioDeAtrasos(
            caminho_do_banco, reiniciar=reiniciar_banco
        )
        self.conectado = threading.Event()
        self.rastreador = RastreadorDeSequencia()
        self.recebidas = 0
        self.aplicadas = 0
        self.descartadas = 0
        self.invalidas = 0
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
            sessao_persistente=self.sessao_persistente,
            sessao_retomada=bool(flags.session_present),
            deduplicacao=self.deduplicar,
        )

    def _ao_desconectar(self, cliente, userdata, flags, reason_code, propriedades):
        self.conectado.clear()
        self.registrador.evento("desconectado", detalhe=str(reason_code))

    def _ao_receber(self, cliente, userdata, mensagem):
        try:
            envelope = Envelope.de_bytes(mensagem.payload)
            evento = topicos.evento_de(mensagem.topic)
        except (EnvelopeInvalido, topicos.TopicoInvalido) as erro:
            self.invalidas += 1
            self.registrador.evento(
                "envelope-invalido", topico=mensagem.topic, detalhe=str(erro)
            )
            return

        self.recebidas += 1
        atraso = envelope.atraso_ms()
        novo = self.repositorio.registrar_mensagem(
            envelope,
            mensagem.topic,
            evento,
            dup=bool(mensagem.dup),
            retain=bool(mensagem.retain),
        )

        if evento == topicos.STATUS:
            self.repositorio.atualizar_status(envelope, envelope.producer_id)
            self.registrador.evento(
                "status-aplicado",
                topico=mensagem.topic,
                estado=envelope.data.get("estado"),
                motivo=envelope.data.get("motivo"),
                message_id=envelope.message_id,
                retain=bool(mensagem.retain),
                testamento=envelope.e_testamento,
                atraso_ms=atraso,
            )
            self._conferir_alvo()
            return

        classificacao, lacuna = self.rastreador.classificar(
            envelope.producer_id, envelope.sequence
        )

        if self.deduplicar and not novo:
            self.descartadas += 1
            self.registrador.evento(
                "duplicado-descartado",
                topico=mensagem.topic,
                tipo=evento,
                sequence=envelope.sequence,
                message_id=envelope.message_id,
                producer_id=envelope.producer_id,
                dup=bool(mensagem.dup),
                detalhe="message_id ja processado",
            )
            self._conferir_alvo()
            return

        if evento == topicos.EMPRESTIMO:
            self.repositorio.aplicar_emprestimo(envelope)
            dias = 0
        else:
            dias = self.repositorio.aplicar_devolucao(envelope)

        self.aplicadas += 1
        self.registrador.evento(
            "aplicado",
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
            dias_de_atraso=dias,
            atraso_ms=atraso,
        )
        self._conferir_alvo()

    def _conferir_alvo(self):
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
        dados = {
            "recebidas": self.recebidas,
            "aplicadas": self.aplicadas,
            "descartadas": self.descartadas,
            "invalidas": self.invalidas,
            "deduplicacao": self.deduplicar,
        }
        dados.update(self.repositorio.resumo())
        return dados

    def encerrar(self):
        self.registrador.evento("resumo", **self.resumo())
        self.cliente.loop_stop()
        self.cliente.disconnect()
        self.repositorio.fechar()
        self.registrador.fechar()


def analisar_argumentos(argumentos=None):
    analisador = argparse.ArgumentParser(
        prog="python -m app.assinantes.servico_atrasos",
        description="Serviço que persiste movimentações e cobra multas de forma idempotente.",
    )
    analisador.add_argument("--id", dest="identificador", default=config.SERVICO_ATRASOS)
    analisador.add_argument("--qos", type=int, choices=(0, 1, 2), default=config.QOS_PADRAO)
    analisador.add_argument("--sem-deduplicacao", action="store_true")
    analisador.add_argument("--sessao-efemera", action="store_true")
    analisador.add_argument("--reiniciar-banco", action="store_true")
    analisador.add_argument("--banco", default=None)
    analisador.add_argument("--filtro", action="append", default=None)
    analisador.add_argument("--ate-mensagens", type=int, default=0)
    analisador.add_argument("--duracao", type=float, default=0.0)
    analisador.add_argument("--silencioso", action="store_true")
    return analisador.parse_args(argumentos)


def main(argumentos=None):
    opcoes = analisar_argumentos(argumentos)
    parada = conexao.Encerramento()
    registrador = Registrador(
        opcoes.identificador, "assinante", silencioso=opcoes.silencioso
    )
    servico = ServicoDeAtrasos(
        opcoes.identificador,
        qos=opcoes.qos,
        deduplicar=not opcoes.sem_deduplicacao,
        sessao_persistente=not opcoes.sessao_efemera,
        reiniciar_banco=opcoes.reiniciar_banco,
        caminho_do_banco=opcoes.banco,
        registrador=registrador,
        filtros=opcoes.filtro or (topicos.FILTRO_DE_TUDO,),
    )
    servico.limite_de_mensagens = opcoes.ate_mensagens or None
    servico.iniciar()
    try:
        parada.aguardar_com_alvo(
            alvo=servico.alvo_atingido if opcoes.ate_mensagens else None,
            limite=opcoes.duracao or None,
        )
    except KeyboardInterrupt:
        pass
    finally:
        servico.encerrar()


if __name__ == "__main__":
    main()
