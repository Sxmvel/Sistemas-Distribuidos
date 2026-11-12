package br.sd.barragem.sensores.entrada.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.Json;
import br.sd.barragem.comum.MensagemSimulacao;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.sensores.aplicacao.SimuladorSensores;
import br.sd.barragem.sensores.dominio.Cenario;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class ReceptorSimulacaoMqtt {

    private final ConexaoMqtt conexao;
    private final SimuladorSensores simulador;

    public ReceptorSimulacaoMqtt(ConexaoMqtt conexao, SimuladorSensores simulador) {
        this.conexao = conexao;
        this.simulador = simulador;
    }

    @PostConstruct
    public void assinar() {
        conexao.assinar(TopicosMqtt.simulacao, (topico, conteudo) -> {
            MensagemSimulacao mensagem = Json.ler(conteudo, MensagemSimulacao.class);
            switch (mensagem.acao()) {
                case MensagemSimulacao.alterarCenario -> simulador.alterarCenario(Cenario.porNome(mensagem.alvo()));
                case MensagemSimulacao.picoSensor -> simulador.injetarPico(mensagem.alvo());
                case MensagemSimulacao.leituraForjada -> simulador.injetarForjada();
                default -> throw new IllegalArgumentException("Ação desconhecida: " + mensagem.acao());
            }
        });
    }
}
