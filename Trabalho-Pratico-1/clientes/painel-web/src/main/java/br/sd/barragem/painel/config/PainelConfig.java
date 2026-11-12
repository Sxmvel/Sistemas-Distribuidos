package br.sd.barragem.painel.config;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.EnderecoControlador;
import br.sd.barragem.comum.ConexaoMqtt;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class PainelConfig {

    @Bean(destroyMethod = "close")
    public ClienteBarragem clienteBarragem() {
        return new ClienteBarragem("centro-monitoramento-web", EnderecoControlador.padrao());
    }

    @Bean(destroyMethod = "close")
    public ConexaoMqtt conexaoMqtt(@Value("${mqtt.url}") String url) {
        ConexaoMqtt conexao = new ConexaoMqtt(url, "painel-laboratorio");
        conexao.conectarEmSegundoPlano();
        return conexao;
    }
}
