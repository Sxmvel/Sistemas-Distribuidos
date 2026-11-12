package br.sd.barragem.controlador.entrada.grpc;

import br.sd.barragem.contrato.ComandoEncaminhado;
import br.sd.barragem.contrato.ConfirmacaoReplicacao;
import br.sd.barragem.contrato.ListaOperacoes;
import br.sd.barragem.contrato.Operacao;
import br.sd.barragem.contrato.PedidoPing;
import br.sd.barragem.contrato.PedidoSincronizacao;
import br.sd.barragem.contrato.RespostaComando;
import br.sd.barragem.contrato.RespostaPing;
import br.sd.barragem.contrato.ServicoReplicacaoGrpc;
import br.sd.barragem.controlador.aplicacao.IndisponivelException;
import br.sd.barragem.controlador.aplicacao.ServicoComandos;
import br.sd.barragem.controlador.aplicacao.ServicoConsulta;
import br.sd.barragem.controlador.aplicacao.ServicoReplicacao;
import br.sd.barragem.controlador.dominio.TipoOperacao;
import br.sd.barragem.controlador.infraestrutura.grpc.ConversorProto;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.springframework.stereotype.Component;

@Component
public class EntradaReplicacaoGrpc extends ServicoReplicacaoGrpc.ServicoReplicacaoImplBase {

    private final ServicoReplicacao replicacao;
    private final ServicoConsulta consulta;
    private final ServicoComandos comandos;

    public EntradaReplicacaoGrpc(ServicoReplicacao replicacao, ServicoConsulta consulta, ServicoComandos comandos) {
        this.replicacao = replicacao;
        this.consulta = consulta;
        this.comandos = comandos;
    }

    @Override
    public void ping(PedidoPing pedido, StreamObserver<RespostaPing> resposta) {
        resposta.onNext(RespostaPing.newBuilder()
                .setId(consulta.meuId())
                .setNivel(ConversorProto.nivel(consulta.nivelParaPares()))
                .setUltimoSeq(consulta.ultimoSeq())
                .addAllQuarentena(consulta.emQuarentena())
                .setInstante(System.currentTimeMillis())
                .build());
        resposta.onCompleted();
    }

    @Override
    public void replicar(Operacao operacao, StreamObserver<ConfirmacaoReplicacao> resposta) {
        boolean aceita = replicacao.receber(ConversorProto.operacao(operacao));
        resposta.onNext(ConfirmacaoReplicacao.newBuilder().setAceita(aceita).setUltimoSeq(replicacao.ultimoSeq()).build());
        resposta.onCompleted();
    }

    @Override
    public void sincronizar(PedidoSincronizacao pedido, StreamObserver<ListaOperacoes> resposta) {
        ListaOperacoes.Builder lista = ListaOperacoes.newBuilder();
        replicacao.desde(pedido.getDesdeSeq()).forEach(op -> lista.addOperacoes(ConversorProto.operacao(op)));
        resposta.onNext(lista.build());
        resposta.onCompleted();
    }

    @Override
    public void encaminharComando(ComandoEncaminhado pedido, StreamObserver<RespostaComando> resposta) {
        try {
            resposta.onNext(ConversorProto.resposta(comandos.executarEncaminhado(TipoOperacao.valueOf(pedido.getTipo()),
                    ConversorProto.pedido(pedido.getPedido()), pedido.getOrigem())));
            resposta.onCompleted();
        } catch (IndisponivelException e) {
            resposta.onError(Status.UNAVAILABLE.withDescription(e.getMessage()).asRuntimeException());
        } catch (RuntimeException e) {
            resposta.onError(Status.INTERNAL.withDescription("falha interna no líder ao executar o comando encaminhado")
                    .asRuntimeException());
        }
    }
}
