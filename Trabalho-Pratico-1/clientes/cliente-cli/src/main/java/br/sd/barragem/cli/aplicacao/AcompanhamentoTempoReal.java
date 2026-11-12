package br.sd.barragem.cli.aplicacao;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.contrato.EstadoSistema;
import io.grpc.Context;
import io.grpc.StatusRuntimeException;
import org.springframework.stereotype.Component;

import java.util.Iterator;
import java.util.List;
import java.util.function.Consumer;

@Component
public class AcompanhamentoTempoReal {

    private final ClienteBarragem cliente;

    public AcompanhamentoTempoReal(ClienteBarragem cliente) {
        this.cliente = cliente;
    }

    public Context.CancellableContext iniciar(Consumer<String> saida) {
        Context.CancellableContext contexto = Context.current().withCancellation();
        Thread leitor = new Thread(() -> contexto.run(() -> acompanhar(contexto, saida)), "acompanhamento");
        leitor.setDaemon(true);
        leitor.start();
        return contexto;
    }

    private void acompanhar(Context.CancellableContext contexto, Consumer<String> saida) {
        List<Integer> controladores = cliente.controladores();
        int indice = Math.max(0, controladores.indexOf(cliente.liderConhecido()));
        while (!contexto.isCancelled()) {
            int id = controladores.get(indice % controladores.size());
            try {
                Iterator<EstadoSistema> fluxo = cliente.acompanhar(id);
                saida.accept("  >> conectado ao fluxo gRPC de c" + id);
                while (fluxo.hasNext()) {
                    saida.accept(Formatador.linhaFluxo(fluxo.next()));
                }
            } catch (StatusRuntimeException e) {
                if (contexto.isCancelled()) {
                    return;
                }
                saida.accept("  >> fluxo de c" + id + " caiu (" + ClienteBarragem.descrever(e) + "), trocando de réplica");
            }
            indice++;
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                return;
            }
        }
    }
}
