package br.sd.barragem.atuadores.entrada.mqtt;

import br.sd.barragem.atuadores.aplicacao.ServicoAtuadores;
import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.Json;
import br.sd.barragem.comum.MensagemComando;
import br.sd.barragem.comum.TopicosMqtt;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

@Component
public class ReceptorComandosMqtt {

    private final ConexaoMqtt conexao;
    private final ServicoAtuadores servico;

    public ReceptorComandosMqtt(ConexaoMqtt conexao, ServicoAtuadores servico) {
        this.conexao = conexao;
        this.servico = servico;
    }

    @PostConstruct
    public void assinar() {
        conexao.assinar(TopicosMqtt.todosComandos, (topico, conteudo) -> {
            MensagemComando comando = Json.ler(conteudo, MensagemComando.class);
            if (comando.autentica()) {
                servico.receber(comando);
            } else {
                servico.rejeitarAssinatura(comando);
            }
        });
    }
}
