package br.sd.barragem.painel.infraestrutura.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.MensagemSimulacao;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.painel.aplicacao.porta.SimuladorCampo;
import org.springframework.stereotype.Component;

@Component
public class SimuladorCampoMqtt implements SimuladorCampo {

    private final ConexaoMqtt conexao;

    public SimuladorCampoMqtt(ConexaoMqtt conexao) {
        this.conexao = conexao;
    }

    @Override
    public void enviar(String acao, String alvo) {
        conexao.publicar(TopicosMqtt.simulacao, new MensagemSimulacao(acao, alvo), false);
    }
}
