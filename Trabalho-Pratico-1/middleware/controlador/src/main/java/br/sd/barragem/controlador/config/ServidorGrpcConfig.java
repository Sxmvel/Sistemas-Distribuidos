package br.sd.barragem.controlador.config;

import io.grpc.BindableService;
import io.grpc.Grpc;
import io.grpc.InsecureServerCredentials;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;

@Component
public class ServidorGrpcConfig implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(ServidorGrpcConfig.class);

    private final PropriedadesControlador propriedades;
    private final List<BindableService> servicos;
    private Server servidor;

    public ServidorGrpcConfig(PropriedadesControlador propriedades, List<BindableService> servicos) {
        this.propriedades = propriedades;
        this.servicos = servicos;
    }

    @Override
    public void start() {
        ServerBuilder<?> construtor = Grpc.newServerBuilderForPort(propriedades.eu().porta(), InsecureServerCredentials.create());
        servicos.forEach(construtor::addService);
        try {
            servidor = construtor.build().start();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        log.info("Controlador c{} ouvindo gRPC na porta {} — pares: {}", propriedades.id(), propriedades.eu().porta(),
                propriedades.pares().stream().map(p -> "c" + p.id() + "@" + p.porta()).toList());
    }

    @Override
    public void stop() {
        if (servidor != null) {
            servidor.shutdownNow();
        }
    }

    @Override
    public boolean isRunning() {
        return servidor != null && !servidor.isShutdown();
    }
}
