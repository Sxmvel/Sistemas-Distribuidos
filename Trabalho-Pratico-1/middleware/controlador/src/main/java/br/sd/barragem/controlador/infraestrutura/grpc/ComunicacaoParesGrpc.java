package br.sd.barragem.controlador.infraestrutura.grpc;

import br.sd.barragem.contrato.ComandoEncaminhado;
import br.sd.barragem.contrato.ListaOperacoes;
import br.sd.barragem.contrato.PedidoPing;
import br.sd.barragem.contrato.PedidoSincronizacao;
import br.sd.barragem.contrato.RespostaPing;
import br.sd.barragem.contrato.ServicoReplicacaoGrpc;
import br.sd.barragem.contrato.TraducaoErros;
import br.sd.barragem.controlador.aplicacao.IndisponivelException;
import br.sd.barragem.controlador.aplicacao.modelo.PedidoOperador;
import br.sd.barragem.controlador.aplicacao.modelo.RespostaPar;
import br.sd.barragem.controlador.aplicacao.modelo.ResultadoComando;
import br.sd.barragem.controlador.aplicacao.porta.ComunicacaoPares;
import br.sd.barragem.controlador.config.PropriedadesControlador;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.TipoOperacao;
import io.grpc.Grpc;
import io.grpc.InsecureChannelCredentials;
import io.grpc.ManagedChannel;
import io.grpc.StatusRuntimeException;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Component
public class ComunicacaoParesGrpc implements ComunicacaoPares, DisposableBean {

    private final Map<Integer, ManagedChannel> canais = new HashMap<>();
    private final int meuId;
    private final long timeoutPingMs;

    public ComunicacaoParesGrpc(PropriedadesControlador propriedades) {
        this.meuId = propriedades.id();
        this.timeoutPingMs = propriedades.timeoutPingMs();
        for (PropriedadesControlador.No par : propriedades.pares()) {
            canais.put(par.id(), Grpc.newChannelBuilderForAddress(par.host(), par.porta(),
                    InsecureChannelCredentials.create()).build());
        }
    }

    private ServicoReplicacaoGrpc.ServicoReplicacaoBlockingStub stub(int parId, long timeoutMs) {
        return ServicoReplicacaoGrpc.newBlockingStub(canais.get(parId)).withDeadlineAfter(timeoutMs, TimeUnit.MILLISECONDS);
    }

    @Override
    public Optional<RespostaPar> ping(int parId) {
        try {
            RespostaPing resposta = stub(parId, timeoutPingMs).ping(PedidoPing.newBuilder().setOrigem(meuId).build());
            return Optional.of(new RespostaPar(resposta.getId(), ConversorProto.nivel(resposta.getNivel()), resposta.getUltimoSeq()));
        } catch (StatusRuntimeException e) {
            canais.get(parId).resetConnectBackoff();
            return Optional.empty();
        }
    }

    @Override
    public boolean replicar(int parId, Operacao operacao) {
        try {
            return stub(parId, 1500).replicar(ConversorProto.operacao(operacao)).getAceita();
        } catch (StatusRuntimeException e) {
            return false;
        }
    }

    @Override
    public List<Operacao> sincronizar(int parId, long desdeSeq) {
        try {
            ListaOperacoes lista = stub(parId, 3000).sincronizar(PedidoSincronizacao.newBuilder().setDesdeSeq(desdeSeq).build());
            return lista.getOperacoesList().stream().map(ConversorProto::operacao).toList();
        } catch (StatusRuntimeException e) {
            return List.of();
        }
    }

    @Override
    public ResultadoComando encaminhar(int liderId, TipoOperacao tipo, PedidoOperador pedido) {
        try {
            return ConversorProto.resposta(stub(liderId, 5000).encaminharComando(ComandoEncaminhado.newBuilder()
                    .setTipo(tipo.name())
                    .setPedido(ConversorProto.pedido(pedido))
                    .setOrigem(meuId)
                    .build()));
        } catch (StatusRuntimeException e) {
            canais.get(liderId).resetConnectBackoff();
            throw new IndisponivelException("líder c" + liderId + " inalcançável a partir de c" + meuId
                    + " (" + TraducaoErros.descrever(e) + ")");
        }
    }

    @Override
    public void destroy() {
        canais.values().forEach(ManagedChannel::shutdownNow);
    }
}
