package br.sd.barragem.atuadores.entrada;

import br.sd.barragem.atuadores.aplicacao.ServicoAtuadores;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AgendadorReavaliacao {

    private final ServicoAtuadores servico;

    public AgendadorReavaliacao(ServicoAtuadores servico) {
        this.servico = servico;
    }

    @Scheduled(fixedRate = 500, initialDelay = 1000)
    public void reavaliar() {
        servico.reavaliar();
    }
}
