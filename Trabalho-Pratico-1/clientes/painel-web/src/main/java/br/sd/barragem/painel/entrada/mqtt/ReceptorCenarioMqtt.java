package br.sd.barragem.painel.entrada.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.Json;
import br.sd.barragem.comum.MensagemSimulacao;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.painel.aplicacao.ServicoLaboratorio;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class ReceptorCenarioMqtt {

    private final ConexaoMqtt conexao;
    private final ServicoLaboratorio laboratorio;

    public ReceptorCenarioMqtt(ConexaoMqtt conexao, ServicoLaboratorio laboratorio) {
        this.conexao = conexao;
        this.laboratorio = laboratorio;
    }

    @PostConstruct
    public void assinar() {
        conexao.assinar(TopicosMqtt.cenarioAtual, (topico, conteudo) ->
                laboratorio.registrarCenario(Json.ler(conteudo, MensagemSimulacao.class).alvo()));
    }
}
