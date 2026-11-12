package br.sd.barragem.cliente;

import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.ListaAuditoria;
import br.sd.barragem.contrato.Modo;
import br.sd.barragem.contrato.PedidoAuditoria;
import br.sd.barragem.contrato.PedidoComando;
import br.sd.barragem.contrato.PedidoEstado;
import br.sd.barragem.contrato.PedidoModo;
import br.sd.barragem.contrato.RespostaComando;
import br.sd.barragem.contrato.ServicoBarragemGrpc;
import br.sd.barragem.contrato.ServicoLaboratorioGrpc;
import br.sd.barragem.contrato.TraducaoErros;
import br.sd.barragem.contrato.Vazio;
import io.grpc.Grpc;
import io.grpc.InsecureChannelCredentials;
import io.grpc.ManagedChannel;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import io.grpc.stub.StreamObserver;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

public class ClienteBarragem implements AutoCloseable {

    private final String nomeCliente;
    private final Map<Integer, ManagedChannel> canais = new LinkedHashMap<>();
    private volatile int liderConhecido;

    public ClienteBarragem(String nomeCliente, List<EnderecoControlador> enderecos) {
        this.nomeCliente = nomeCliente;
        for (EnderecoControlador endereco : enderecos) {
            canais.put(endereco.id(), Grpc.newChannelBuilderForAddress(endereco.host(), endereco.porta(),
                    InsecureChannelCredentials.create()).build());
        }
        this.liderConhecido = enderecos.get(0).id();
    }

    public List<Integer> controladores() {
        return List.copyOf(canais.keySet());
    }

    public int liderConhecido() {
        return liderConhecido;
    }

    private ServicoBarragemGrpc.ServicoBarragemBlockingStub barragem(int id, long timeoutMs) {
        return ServicoBarragemGrpc.newBlockingStub(canais.get(id)).withDeadlineAfter(timeoutMs, TimeUnit.MILLISECONDS);
    }

    private ServicoLaboratorioGrpc.ServicoLaboratorioBlockingStub laboratorio(int id) {
        return ServicoLaboratorioGrpc.newBlockingStub(canais.get(id)).withDeadlineAfter(2, TimeUnit.SECONDS);
    }

    public ResultadoVotacao consultarComVotacao() {
        Map<Integer, EstadoSistema> respostas = new ConcurrentHashMap<>();
        Map<Integer, String> falhas = new ConcurrentHashMap<>();
        List<CompletableFuture<Void>> chamadas = new ArrayList<>();
        for (int id : canais.keySet()) {
            chamadas.add(CompletableFuture.runAsync(() -> {
                try {
                    respostas.put(id, barragem(id, 800).obterEstado(PedidoEstado.newBuilder().setCliente(nomeCliente).build()));
                } catch (StatusRuntimeException e) {
                    falhas.put(id, descrever(e));
                    canais.get(id).resetConnectBackoff();
                }
            }));
        }
        CompletableFuture.allOf(chamadas.toArray(CompletableFuture[]::new)).join();
        ResultadoVotacao resultado = Votacao.apurar(respostas, falhas, canais.size());
        if (resultado.liderId() > 0) {
            liderConhecido = resultado.liderId();
        }
        return resultado;
    }

    public ResultadoExecucao executar(TipoComando tipo, String operador, String motivo) {
        String requisicaoId = UUID.randomUUID().toString();
        PedidoComando pedido = PedidoComando.newBuilder()
                .setRequisicaoId(requisicaoId)
                .setOperador(operador)
                .setMotivo(motivo == null ? "" : motivo)
                .build();
        List<ResultadoExecucao.Tentativa> tentativas = new ArrayList<>();
        long limite = System.currentTimeMillis() + 15000;
        while (System.currentTimeMillis() < limite) {
            for (int id : ordemDeTentativa()) {
                long inicio = System.currentTimeMillis();
                try {
                    RespostaComando resposta = chamar(tipo, barragem(id, 6000), pedido);
                    tentativas.add(new ResultadoExecucao.Tentativa(id, true, resposta.getMensagem(),
                            System.currentTimeMillis() - inicio));
                    liderConhecido = resposta.getExecutadoPor();
                    return new ResultadoExecucao(requisicaoId, tipo, Optional.of(resposta), tentativas);
                } catch (StatusRuntimeException e) {
                    tentativas.add(new ResultadoExecucao.Tentativa(id, false, descrever(e),
                            System.currentTimeMillis() - inicio));
                    canais.get(id).resetConnectBackoff();
                    if (e.getStatus().getCode() == Status.Code.INVALID_ARGUMENT) {
                        return new ResultadoExecucao(requisicaoId, tipo, Optional.empty(), tentativas);
                    }
                }
            }
            esperar(800);
        }
        return new ResultadoExecucao(requisicaoId, tipo, Optional.empty(), tentativas);
    }

    private List<Integer> ordemDeTentativa() {
        List<Integer> ordem = new ArrayList<>();
        if (canais.containsKey(liderConhecido)) {
            ordem.add(liderConhecido);
        }
        canais.keySet().stream().filter(id -> id != liderConhecido).forEach(ordem::add);
        return ordem;
    }

    private static RespostaComando chamar(TipoComando tipo, ServicoBarragemGrpc.ServicoBarragemBlockingStub stub,
                                          PedidoComando pedido) {
        return switch (tipo) {
            case acionarEvacuacao -> stub.acionarEvacuacao(pedido);
            case reconhecerAlarme -> stub.reconhecerAlarme(pedido);
            case encerrarEvacuacao -> stub.encerrarEvacuacao(pedido);
        };
    }

    public Optional<ListaAuditoria> auditoria(int limite) {
        for (int id : ordemDeTentativa()) {
            try {
                return Optional.of(barragem(id, 1000).listarAuditoria(PedidoAuditoria.newBuilder().setLimite(limite).build()));
            } catch (StatusRuntimeException e) {
                canais.get(id).resetConnectBackoff();
            }
        }
        return Optional.empty();
    }

    public Iterator<EstadoSistema> acompanhar(int id) {
        return ServicoBarragemGrpc.newBlockingStub(canais.get(id))
                .acompanharEstado(PedidoEstado.newBuilder().setCliente(nomeCliente).build());
    }

    public void acompanharAssincrono(int id, Consumer<EstadoSistema> aoReceber, Consumer<Throwable> aoFalhar) {
        ServicoBarragemGrpc.newStub(canais.get(id)).acompanharEstado(PedidoEstado.newBuilder().setCliente(nomeCliente).build(),
                new StreamObserver<>() {
                    @Override
                    public void onNext(EstadoSistema estado) {
                        aoReceber.accept(estado);
                    }

                    @Override
                    public void onError(Throwable erro) {
                        aoFalhar.accept(erro);
                    }

                    @Override
                    public void onCompleted() {
                        aoFalhar.accept(new IllegalStateException("fluxo encerrado pelo servidor"));
                    }
                });
    }

    public String definirModo(int id, Modo modo) {
        return laboratorio(id).definirModo(PedidoModo.newBuilder().setModo(modo).build()).getMensagem();
    }

    public String falharNoProximoComando(int id) {
        return laboratorio(id).falharNoProximoComando(Vazio.getDefaultInstance()).getMensagem();
    }

    public String desligar(int id) {
        return laboratorio(id).desligar(Vazio.getDefaultInstance()).getMensagem();
    }

    public static String descrever(StatusRuntimeException e) {
        return TraducaoErros.descrever(e);
    }

    private static void esperar(long milissegundos) {
        try {
            Thread.sleep(milissegundos);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Override
    public void close() {
        canais.values().forEach(ManagedChannel::shutdownNow);
    }
}
