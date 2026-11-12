package br.sd.barragem.controlador.entrada.mqtt;

import br.sd.barragem.comum.ConexaoMqtt;
import br.sd.barragem.comum.Json;
import br.sd.barragem.comum.MensagemEstadoAtuador;
import br.sd.barragem.comum.TopicosMqtt;
import br.sd.barragem.controlador.aplicacao.EstadoAtuadoresConhecidos;
import br.sd.barragem.controlador.aplicacao.modelo.EstadoAtuadorConhecido;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class ReceptorEstadoAtuadoresMqtt {

    private final ConexaoMqtt conexao;
    private final EstadoAtuadoresConhecidos atuadores;

    public ReceptorEstadoAtuadoresMqtt(ConexaoMqtt conexao, EstadoAtuadoresConhecidos atuadores) {
        this.conexao = conexao;
        this.atuadores = atuadores;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void assinar() {
        conexao.assinar(TopicosMqtt.todosEstadosAtuadores, (topico, conteudo) -> {
            MensagemEstadoAtuador mensagem = Json.ler(conteudo, MensagemEstadoAtuador.class);
            atuadores.atualizar(new EstadoAtuadorConhecido(mensagem.atuadorId(), mensagem.tipo(), mensagem.estado(),
                    mensagem.apoiadores() == null ? List.of() : mensagem.apoiadores(), mensagem.instante()));
        });
    }
}
