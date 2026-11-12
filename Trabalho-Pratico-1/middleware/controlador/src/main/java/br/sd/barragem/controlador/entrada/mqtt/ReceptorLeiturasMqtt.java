package br.sd.barragem.controlador.entrada.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.Json;
import br.sd.barragem.comum.MensagemLeitura;
import br.sd.barragem.comum.TipoSensor;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.controlador.aplicacao.ServicoMonitoramento;
import br.sd.barragem.controlador.dominio.Leitura;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class ReceptorLeiturasMqtt {

    private final ConexaoMqtt conexao;
    private final ServicoMonitoramento monitoramento;

    public ReceptorLeiturasMqtt(ConexaoMqtt conexao, ServicoMonitoramento monitoramento) {
        this.conexao = conexao;
        this.monitoramento = monitoramento;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void assinar() {
        conexao.assinar(TopicosMqtt.todasLeituras, (topico, conteudo) -> {
            MensagemLeitura mensagem = Json.ler(conteudo, MensagemLeitura.class);
            if (!mensagem.autentica()) {
                monitoramento.rejeitarAssinatura(mensagem.sensorId(), mensagem.valor());
                return;
            }
            monitoramento.processar(new Leitura(mensagem.sensorId(), TipoSensor.valueOf(mensagem.tipo()),
                    mensagem.valor(), mensagem.instante()));
        });
    }
}
