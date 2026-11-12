package br.sd.barragem.sensores.infraestrutura.mqtt;

import br.sd.barragem.comum.Assinatura;
import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.MensagemLeitura;
import br.sd.barragem.comum.MensagemSimulacao;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.sensores.aplicacao.porta.PublicadorLeituras;
import br.sd.barragem.sensores.dominio.LeituraGerada;
import org.springframework.stereotype.Component;

@Component
public class PublicadorLeiturasMqtt implements PublicadorLeituras {

    private static final String chaveDoInvasor = "chave-adivinhada-pelo-invasor";

    private final ConexaoMqtt conexao;

    public PublicadorLeiturasMqtt(ConexaoMqtt conexao) {
        this.conexao = conexao;
    }

    @Override
    public void publicar(LeituraGerada leitura) {
        MensagemLeitura mensagem = new MensagemLeitura(leitura.sensorId(), leitura.tipo().name(), leitura.valor(),
                leitura.tipo().unidade(), leitura.instante(), leitura.sequencia(), null);
        String chave = leitura.forjada() ? chaveDoInvasor : Assinatura.chaveSensor(leitura.sensorId());
        conexao.publicar(TopicosMqtt.leitura(leitura.tipo().name(), leitura.sensorId()), mensagem.assinada(chave), false);
    }

    @Override
    public void publicarCenario(String cenario) {
        conexao.publicar(TopicosMqtt.cenarioAtual, new MensagemSimulacao(MensagemSimulacao.alterarCenario, cenario), true);
    }
}
