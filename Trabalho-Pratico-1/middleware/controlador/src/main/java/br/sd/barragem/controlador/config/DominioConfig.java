package br.sd.barragem.controlador.config;

import br.sd.barragem.controlador.dominio.AvaliadorRisco;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.PoliticaAtuadores;
import br.sd.barragem.controlador.dominio.VerificadorPlausibilidade;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DominioConfig {

    @Bean
    public AvaliadorRisco avaliadorRisco(@Value("${controlador.persistencia-leituras:3}") int persistencia) {
        return new AvaliadorRisco(persistencia);
    }

    @Bean
    public VerificadorPlausibilidade verificadorPlausibilidade(@Value("${controlador.janela-tempo-ms:10000}") long janela) {
        return new VerificadorPlausibilidade(janela);
    }

    @Bean
    public EstadoBarragem estadoBarragem(AvaliadorRisco avaliador,
                                         @Value("${controlador.histerese-descida-ms:15000}") long histerese) {
        return new EstadoBarragem(avaliador, histerese);
    }

    @Bean
    public PoliticaAtuadores politicaAtuadores() {
        return new PoliticaAtuadores();
    }

    @Bean
    public VisaoCluster visaoCluster(PropriedadesControlador propriedades,
                                     @Value("${controlador.limite-quarentena:9}") int limiteQuarentena,
                                     @Value("${controlador.teto-suspeita:15}") int tetoSuspeita) {
        return new VisaoCluster(propriedades.id(),
                propriedades.pares().stream().map(PropriedadesControlador.No::id).toList(),
                limiteQuarentena, tetoSuspeita);
    }
}
