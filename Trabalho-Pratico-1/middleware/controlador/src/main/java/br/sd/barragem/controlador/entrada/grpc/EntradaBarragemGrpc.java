package br.sd.barragem.controlador.entrada.grpc;

import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.ListaAuditoria;
import br.sd.barragem.contrato.PedidoAuditoria;
import br.sd.barragem.contrato.PedidoComando;
import br.sd.barragem.contrato.PedidoEstado;
import br.sd.barragem.contrato.RespostaComando;
import br.sd.barragem.contrato.ServicoBarragemGrpc;
import br.sd.barragem.controlador.aplicacao.IndisponivelException;
import br.sd.barragem.controlador.aplicacao.ServicoComandos;
import br.sd.barragem.controlador.aplicacao.ServicoConsulta;
import br.sd.barragem.controlador.dominio.TipoOperacao;
import br.sd.barragem.controlador.infraestrutura.grpc.ConversorProto;
import io.grpc.Status;
import io.grpc.stub.ServerCallStreamObserver;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.stereotype.Component;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class EntradaBarragemGrpc extends ServicoBarragemGrpc.ServicoBarragemImplBase implements DisposableBean {

    private static final Logger log = LoggerFactory.getLogger(EntradaBarragemGrpc.class);

    private final ServicoConsulta consulta;
    private final ServicoComandos comandos;
    private final ScheduledExecutorService transmissor = Executors.newScheduledThreadPool(2);

    public EntradaBarragemGrpc(ServicoConsulta consulta, ServicoComandos comandos) {
        this.consulta = consulta;
        this.comandos = comandos;
    }

    @Override
    public void obterEstado(PedidoEstado pedido, StreamObserver<EstadoSistema> resposta) {
        resposta.onNext(ConversorProto.estado(consulta.retratoParaCliente()));
        resposta.onCompleted();
    }

    @Override
    public void acompanharEstado(PedidoEstado pedido, StreamObserver<EstadoSistema> resposta) {
        ServerCallStreamObserver<EstadoSistema> fluxo = (ServerCallStreamObserver<EstadoSistema>) resposta;
        AtomicReference<ScheduledFuture<?>> tarefa = new AtomicReference<>();
        fluxo.setOnCancelHandler(() -> cancelar(tarefa));
        tarefa.set(transmissor.scheduleAtFixedRate(() -> {
            if (fluxo.isCancelled()) {
                cancelar(tarefa);
                return;
            }
            try {
                synchronized (fluxo) {
                    fluxo.onNext(ConversorProto.estado(consulta.retratoParaCliente()));
                }
            } catch (RuntimeException e) {
                cancelar(tarefa);
            }
        }, 0, 1, TimeUnit.SECONDS));
    }

    private static void cancelar(AtomicReference<ScheduledFuture<?>> tarefa) {
        ScheduledFuture<?> atual = tarefa.get();
        if (atual != null) {
            atual.cancel(false);
        }
    }

    @Override
    public void acionarEvacuacao(PedidoComando pedido, StreamObserver<RespostaComando> resposta) {
        executar(TipoOperacao.acionarEvacuacao, pedido, resposta);
    }

    @Override
    public void reconhecerAlarme(PedidoComando pedido, StreamObserver<RespostaComando> resposta) {
        executar(TipoOperacao.reconhecerAlarme, pedido, resposta);
    }

    @Override
    public void encerrarEvacuacao(PedidoComando pedido, StreamObserver<RespostaComando> resposta) {
        executar(TipoOperacao.encerrarEvacuacao, pedido, resposta);
    }

    @Override
    public void listarAuditoria(PedidoAuditoria pedido, StreamObserver<ListaAuditoria> resposta) {
        int limite = pedido.getLimite() <= 0 ? 30 : Math.min(pedido.getLimite(), 200);
        ListaAuditoria.Builder lista = ListaAuditoria.newBuilder().setControladorId(consulta.meuId());
        consulta.auditoria(limite).forEach(r -> lista.addEventos(ConversorProto.evento(r)));
        resposta.onNext(lista.build());
        resposta.onCompleted();
    }

    private void executar(TipoOperacao tipo, PedidoComando pedido, StreamObserver<RespostaComando> resposta) {
        if (pedido.getRequisicaoId().isBlank()) {
            resposta.onError(Status.INVALID_ARGUMENT.withDescription("requisicao_id é obrigatório").asRuntimeException());
            return;
        }
        try {
            resposta.onNext(ConversorProto.resposta(comandos.executar(tipo, ConversorProto.pedido(pedido))));
            resposta.onCompleted();
        } catch (IndisponivelException e) {
            resposta.onError(Status.UNAVAILABLE.withDescription(e.getMessage()).asRuntimeException());
        } catch (RuntimeException e) {
            log.error("Falha interna ao executar {}: {}", tipo, e.toString());
            resposta.onError(Status.INTERNAL.withDescription("falha interna no controlador ao executar o comando")
                    .asRuntimeException());
        }
    }

    @Override
    public void destroy() {
        transmissor.shutdownNow();
    }
}
