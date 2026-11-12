package br.sd.barragem.sensores.aplicacao;

import br.sd.barragem.comum.Dispositivos;
import br.sd.barragem.sensores.aplicacao.porta.PublicadorLeituras;
import br.sd.barragem.sensores.dominio.Cenario;
import br.sd.barragem.sensores.dominio.LeituraGerada;
import br.sd.barragem.sensores.dominio.SensorSimulado;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.stream.Collectors;

@Service
public class SimuladorSensores {

    private static final Logger log = LoggerFactory.getLogger(SimuladorSensores.class);

    private final PublicadorLeituras publicador;
    private final List<SensorSimulado> sensores = new ArrayList<>();
    private final Random aleatorio = new Random();
    private Cenario cenario = Cenario.normal;
    private long inicioCenario = System.currentTimeMillis();
    private String picoPendente;
    private boolean forjadaPendente;

    public SimuladorSensores(PublicadorLeituras publicador) {
        this.publicador = publicador;
        for (Dispositivos.Sensor sensor : Dispositivos.sensores) {
            sensores.add(new SensorSimulado(sensor.id(), sensor.tipo(), base(sensor)));
        }
        publicador.publicarCenario(cenario.name());
    }

    private static double base(Dispositivos.Sensor sensor) {
        return switch (sensor.id()) {
            case "PZ-01" -> 90;
            case "PZ-02" -> 110;
            case "PZ-03" -> 85;
            case "IN-01" -> 0.25;
            case "IN-02" -> 0.15;
            case "NV-01" -> 72;
            case "PL-01" -> 2;
            case "TB-01" -> 25;
            default -> 0;
        };
    }

    public synchronized void passo() {
        double segundos = (System.currentTimeMillis() - inicioCenario) / 1000.0;
        List<LeituraGerada> leituras = new ArrayList<>();
        for (SensorSimulado sensor : sensores) {
            if (sensor.id().equals(picoPendente)) {
                leituras.add(sensor.pico());
                log.warn("Falha injetada: pico espúrio em {}", sensor.id());
            } else {
                leituras.add(sensor.avancar(cenario, segundos, aleatorio));
            }
        }
        picoPendente = null;
        if (forjadaPendente) {
            leituras.add(sensores.get(0).forjada());
            log.warn("Ataque injetado: leitura forjada para {} com assinatura inválida", sensores.get(0).id());
            forjadaPendente = false;
        }
        leituras.forEach(publicador::publicar);
        log.info("[{} t={}s] {}", cenario.descricao(), (long) segundos, resumo(leituras));
    }

    public synchronized void alterarCenario(Cenario novo) {
        cenario = novo;
        inicioCenario = System.currentTimeMillis();
        publicador.publicarCenario(novo.name());
        log.warn(">>> Cenário alterado para: {}", novo.descricao());
    }

    public synchronized void injetarPico(String sensorId) {
        picoPendente = sensorId;
    }

    public synchronized void injetarForjada() {
        forjadaPendente = true;
    }

    private static String resumo(List<LeituraGerada> leituras) {
        return leituras.stream()
                .filter(l -> !l.forjada())
                .map(l -> String.format(Locale.ROOT, "%s=%.1f", l.sensorId(), l.valor()))
                .collect(Collectors.joining(" "));
    }
}
