package br.sd.barragem.controlador.entrada.grpc;

import br.sd.barragem.contrato.PedidoModo;
import br.sd.barragem.contrato.RespostaLaboratorio;
import br.sd.barragem.contrato.ServicoLaboratorioGrpc;
import br.sd.barragem.contrato.Vazio;
import br.sd.barragem.controlador.aplicacao.ControleLaboratorio;
import br.sd.barragem.controlador.dominio.ModoOperacao;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class EntradaLaboratorioGrpc extends ServicoLaboratorioGrpc.ServicoLaboratorioImplBase {

    private static final Logger log = LoggerFactory.getLogger(EntradaLaboratorioGrpc.class);

    private final ControleLaboratorio laboratorio;
    private final int meuId;

    public EntradaLaboratorioGrpc(ControleLaboratorio laboratorio, VisaoCluster visao) {
        this.laboratorio = laboratorio;
        this.meuId = visao.meuId();
    }

    @Override
    public void definirModo(PedidoModo pedido, StreamObserver<RespostaLaboratorio> resposta) {
        ModoOperacao modo = ModoOperacao.values()[pedido.getModo().getNumber()];
        laboratorio.definirModo(modo);
        responder(resposta, "c" + meuId + " agora em modo " + modo);
    }

    @Override
    public void falharNoProximoComando(Vazio pedido, StreamObserver<RespostaLaboratorio> resposta) {
        laboratorio.armarFalha();
        responder(resposta, "c" + meuId + " vai cair após replicar o próximo comando");
    }

    @Override
    public void desligar(Vazio pedido, StreamObserver<RespostaLaboratorio> resposta) {
        responder(resposta, "c" + meuId + " desligando");
        Thread desligamento = new Thread(() -> {
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            log.error("LABORATÓRIO: queda simulada do processo");
            Runtime.getRuntime().halt(1);
        });
        desligamento.start();
    }

    private void responder(StreamObserver<RespostaLaboratorio> resposta, String mensagem) {
        resposta.onNext(RespostaLaboratorio.newBuilder().setControladorId(meuId).setMensagem(mensagem).build());
        resposta.onCompleted();
    }
}
