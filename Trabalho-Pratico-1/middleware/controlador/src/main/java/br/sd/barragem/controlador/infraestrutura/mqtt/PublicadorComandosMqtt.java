package br.sd.barragem.controlador.infraestrutura.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.MensagemComando;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.controlador.aplicacao.porta.PublicadorComandos;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.springframework.stereotype.Component;

@Component
public class PublicadorComandosMqtt implements PublicadorComandos {

    private final ConexaoMqtt conexao;
    private final int meuId;

    public PublicadorComandosMqtt(ConexaoMqtt conexao, VisaoCluster visao) {
        this.conexao = conexao;
        this.meuId = visao.meuId();
    }

    @Override
    public void publicar(String atuadorId, String estado) {
        MensagemComando comando = new MensagemComando(atuadorId, estado, meuId, System.currentTimeMillis(), null);
        conexao.publicar(TopicosMqtt.comando(atuadorId), comando.assinada(), false);
    }
}
