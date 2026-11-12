package br.sd.barragem.broker;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class BrokerMqttApplication {

    public static void main(String[] args) {
        SpringApplication.run(BrokerMqttApplication.class, args);
    }
}
