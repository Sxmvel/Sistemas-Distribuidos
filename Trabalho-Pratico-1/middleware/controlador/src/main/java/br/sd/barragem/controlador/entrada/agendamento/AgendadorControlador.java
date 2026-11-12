package br.sd.barragem.controlador.entrada.agendamento;

import br.sd.barragem.controlador.aplicacao.ServicoAtuacao;
import br.sd.barragem.controlador.aplicacao.ServicoCluster;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AgendadorControlador {

    private final ServicoCluster cluster;
    private final ServicoAtuacao atuacao;

    public AgendadorControlador(ServicoCluster cluster, ServicoAtuacao atuacao) {
        this.cluster = cluster;
        this.atuacao = atuacao;
    }

    @Scheduled(fixedDelayString = "${controlador.intervalo-heartbeat-ms:1000}", initialDelay = 500)
    public void heartbeat() {
        cluster.rodadaHeartbeat();
    }

    @Scheduled(fixedRate = 1000, initialDelay = 5000)
    public void comandarAtuadores() {
        atuacao.publicarComandos();
    }
}
