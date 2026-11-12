package br.sd.barragem.broker;

import io.moquette.broker.Server;
import io.moquette.broker.config.MemoryConfig;
import io.moquette.interception.AbstractInterceptHandler;
import io.moquette.interception.messages.InterceptConnectMessage;
import io.moquette.interception.messages.InterceptConnectionLostMessage;
import io.moquette.interception.messages.InterceptDisconnectMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Properties;

@Component
public class BrokerMqtt implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(BrokerMqtt.class);

    private final Server servidor = new Server();
    private final int porta;
    private volatile boolean ativo;

    public BrokerMqtt(@Value("${broker.porta:1883}") int porta) {
        this.porta = porta;
    }

    @Override
    public void start() {
        Properties propriedades = new Properties();
        propriedades.setProperty("host", "0.0.0.0");
        propriedades.setProperty("port", String.valueOf(porta));
        propriedades.setProperty("allow_anonymous", "true");
        propriedades.setProperty("persistence_enabled", "false");
        propriedades.setProperty("telemetry_enabled", "false");
        try {
            servidor.startServer(new MemoryConfig(propriedades), List.of(new MonitorConexoes()));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        ativo = true;
        log.info("Broker MQTT ativo na porta {}", porta);
    }

    @Override
    public void stop() {
        servidor.stopServer();
        ativo = false;
    }

    @Override
    public boolean isRunning() {
        return ativo;
    }

    private static class MonitorConexoes extends AbstractInterceptHandler {

        @Override
        public String getID() {
            return "monitor-conexoes";
        }

        @Override
        public void onConnect(InterceptConnectMessage mensagem) {
            log.info("Cliente conectado: {}", mensagem.getClientID());
        }

        @Override
        public void onDisconnect(InterceptDisconnectMessage mensagem) {
            log.info("Cliente desconectado: {}", mensagem.getClientID());
        }

        @Override
        public void onConnectionLost(InterceptConnectionLostMessage mensagem) {
            log.warn("Conexão perdida: {}", mensagem.getClientID());
        }

        @Override
        public void onSessionLoopError(Throwable erro) {
            log.error("Erro no broker: {}", erro.getMessage());
        }
    }
}
