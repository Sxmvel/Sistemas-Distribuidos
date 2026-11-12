package br.sd.barragem.atuadores.config;

import br.sd.barragem.comum.ConexaoMqtt;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MqttConfig {

    @Bean(destroyMethod = "close")
    public ConexaoMqtt conexaoMqtt(@Value("${mqtt.url}") String url) {
        ConexaoMqtt conexao = new ConexaoMqtt(url, "atuadores");
        conexao.conectar();
        return conexao;
    }
}
