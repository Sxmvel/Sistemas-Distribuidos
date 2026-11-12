package br.sd.barragem.atuadores;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AtuadoresApplication {

    public static void main(String[] args) {
        SpringApplication.run(AtuadoresApplication.class, args);
    }
}
