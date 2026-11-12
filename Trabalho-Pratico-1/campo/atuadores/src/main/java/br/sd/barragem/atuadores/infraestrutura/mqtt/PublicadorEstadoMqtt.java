package br.sd.barragem.atuadores.infraestrutura.mqtt;

import br.sd.barragem.atuadores.aplicacao.porta.PublicadorEstadoAtuador;
import br.sd.barragem.atuadores.dominio.AtuadorFisico;
import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.MensagemEstadoAtuador;
import br.sd.barragem.comum.TopicosMqtt;
import org.springframework.stereotype.Component;

@Component
public class PublicadorEstadoMqtt implements PublicadorEstadoAtuador {

    private final ConexaoMqtt conexao;

    public PublicadorEstadoMqtt(ConexaoMqtt conexao) {
        this.conexao = conexao;
    }

    @Override
    public void publicar(AtuadorFisico atuador) {
        MensagemEstadoAtuador mensagem = new MensagemEstadoAtuador(atuador.id(), atuador.tipo().name(),
                atuador.estado(), atuador.apoiadores(), atuador.ultimaMudanca());
        conexao.publicar(TopicosMqtt.estadoAtuador(atuador.id()), mensagem, true);
    }
}
