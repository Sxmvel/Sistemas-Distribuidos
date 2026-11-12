package br.sd.barragem.cli.config;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.EnderecoControlador;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ClienteConfig {

    @Bean(destroyMethod = "close")
    public ClienteBarragem clienteBarragem() {
        return new ClienteBarragem("defesa-civil-cli", EnderecoControlador.padrao());
    }
}
