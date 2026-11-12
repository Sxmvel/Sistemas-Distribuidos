package br.sd.barragem.controlador.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@ConfigurationProperties("controlador")
public record PropriedadesControlador(int id, long timeoutPingMs, List<No> cluster) {

    public record No(int id, String host, int porta) {
    }

    public No eu() {
        return cluster.stream().filter(n -> n.id() == id).findFirst()
                .orElseThrow(() -> new IllegalStateException("controlador.id=" + id + " não está em controlador.cluster"));
    }

    public List<No> pares() {
        return cluster.stream().filter(n -> n.id() != id).toList();
    }
}
