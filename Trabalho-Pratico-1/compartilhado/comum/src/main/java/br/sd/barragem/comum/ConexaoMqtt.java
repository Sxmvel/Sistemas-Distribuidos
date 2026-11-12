package br.sd.barragem.comum;

import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;

public class ConexaoMqtt implements AutoCloseable {

    private static final Logger log = LoggerFactory.getLogger(ConexaoMqtt.class);

    private final MqttClient cliente;
    private final Map<String, BiConsumer<String, byte[]>> assinaturas = new ConcurrentHashMap<>();

    public ConexaoMqtt(String url, String clienteId) {
        try {
            this.cliente = new MqttClient(url, clienteId, new MemoryPersistence());
        } catch (MqttException e) {
            throw new IllegalStateException("Não foi possível criar o cliente MQTT (código " + e.getReasonCode() + ")", e);
        }
        cliente.setCallback(new MqttCallbackExtended() {
            @Override
            public void connectComplete(boolean reconexao, String servidor) {
                if (reconexao) {
                    log.info("Reconectado ao broker {}", servidor);
                }
                assinaturas.forEach(ConexaoMqtt.this::registrar);
            }

            @Override
            public void connectionLost(Throwable causa) {
                log.warn("Conexão com o broker MQTT perdida — tentando reconectar");
            }

            @Override
            public void messageArrived(String topico, MqttMessage mensagem) {
            }

            @Override
            public void deliveryComplete(IMqttDeliveryToken token) {
            }
        });
    }

    public void conectar() {
        MqttConnectOptions opcoes = new MqttConnectOptions();
        opcoes.setAutomaticReconnect(true);
        opcoes.setCleanSession(true);
        opcoes.setConnectionTimeout(3);
        opcoes.setKeepAliveInterval(10);
        opcoes.setMaxInflight(1000);
        while (!cliente.isConnected()) {
            try {
                cliente.connect(opcoes);
                log.info("Conectado ao broker MQTT {}", cliente.getServerURI());
            } catch (MqttException e) {
                log.warn("Broker MQTT indisponível (código {}), nova tentativa em 2s", e.getReasonCode());
                esperar(2000);
            }
        }
    }

    public void conectarEmSegundoPlano() {
        Thread conexao = new Thread(this::conectar, "conexao-mqtt");
        conexao.setDaemon(true);
        conexao.start();
    }

    public void publicar(String topico, Object mensagem, boolean retida) {
        try {
            cliente.publish(topico, Json.escrever(mensagem), 1, retida);
        } catch (MqttException e) {
            log.debug("Falha ao publicar em {} (código {})", topico, e.getReasonCode());
        }
    }

    public void assinar(String filtro, BiConsumer<String, byte[]> tratador) {
        assinaturas.put(filtro, tratador);
        registrar(filtro, tratador);
    }

    private void registrar(String filtro, BiConsumer<String, byte[]> tratador) {
        if (!cliente.isConnected()) {
            return;
        }
        try {
            cliente.subscribe(filtro, 1, (topico, mensagem) -> {
                try {
                    tratador.accept(topico, mensagem.getPayload());
                } catch (RuntimeException e) {
                    log.warn("Mensagem ignorada em {}: {}", topico, e.getMessage());
                }
            });
        } catch (MqttException e) {
            log.warn("Falha ao assinar {} (código {})", filtro, e.getReasonCode());
        }
    }

    @Override
    public void close() {
        try {
            if (cliente.isConnected()) {
                cliente.disconnect(500);
            }
            cliente.close();
        } catch (MqttException e) {
            log.debug("Falha ao fechar a conexão MQTT (código {})", e.getReasonCode());
        }
    }

    private static void esperar(long milissegundos) {
        try {
            Thread.sleep(milissegundos);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
