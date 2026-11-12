package br.sd.barragem.painel;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class PainelWebApplication {

    public static void main(String[] args) {
        SpringApplication.run(PainelWebApplication.class, args);
    }
}
