package br.sd.barragem.sensores.entrada;

import br.sd.barragem.sensores.aplicacao.SimuladorSensores;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AgendadorLeituras {

    private final SimuladorSensores simulador;

    public AgendadorLeituras(SimuladorSensores simulador) {
        this.simulador = simulador;
    }

    @Scheduled(fixedRateString = "${sensores.intervalo-ms:1000}", initialDelay = 1000)
    public void publicarLeituras() {
        simulador.passo();
    }
}
