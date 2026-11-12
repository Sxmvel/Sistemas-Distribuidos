package br.sd.barragem.comum;

import java.util.List;
import java.util.Optional;

public final class Dispositivos {

    public record Sensor(String id, TipoSensor tipo, String local) {
    }

    public record Atuador(String id, TipoAtuador tipo, String local) {
    }

    public static final String barragem = "Barragem Serra Azul (fictícia)";

    public static final List<Sensor> sensores = List.of(
            new Sensor("PZ-01", TipoSensor.piezometro, "Maciço - crista"),
            new Sensor("PZ-02", TipoSensor.piezometro, "Maciço - fundação"),
            new Sensor("PZ-03", TipoSensor.piezometro, "Ombreira esquerda"),
            new Sensor("IN-01", TipoSensor.deslocamento, "Talude de jusante"),
            new Sensor("IN-02", TipoSensor.deslocamento, "Crista"),
            new Sensor("NV-01", TipoSensor.nivel, "Reservatório"),
            new Sensor("PL-01", TipoSensor.chuva, "Estação meteorológica"),
            new Sensor("TB-01", TipoSensor.turbidez, "Saída do dreno de pé"));

    public static final List<Atuador> atuadores = List.of(
            new Atuador("SR-01", TipoAtuador.sirene, "ZAS - Vila Esperança"),
            new Atuador("SR-02", TipoAtuador.sirene, "ZAS - Comunidade do Córrego"),
            new Atuador("PR-01", TipoAtuador.painelRota, "Rota de fuga principal"),
            new Atuador("CN-01", TipoAtuador.cancela, "Estrada de acesso à ZAS"),
            new Atuador("BR-01", TipoAtuador.bomba, "Poço de rebaixamento"));

    private Dispositivos() {
    }

    public static Optional<Sensor> sensor(String id) {
        return sensores.stream().filter(s -> s.id().equals(id)).findFirst();
    }

    public static Optional<Atuador> atuador(String id) {
        return atuadores.stream().filter(a -> a.id().equals(id)).findFirst();
    }
}
