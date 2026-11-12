package br.sd.barragem.painel.aplicacao;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.TipoComando;
import br.sd.barragem.painel.aplicacao.modelo.ResultadoComandoVisao;
import org.springframework.stereotype.Service;

@Service
public class ServicoOperacao {

    private final ClienteBarragem cliente;

    public ServicoOperacao(ClienteBarragem cliente) {
        this.cliente = cliente;
    }

    public ResultadoComandoVisao executar(TipoComando tipo, String operador, String motivo) {
        return ResultadoComandoVisao.de(cliente.executar(tipo, operador, motivo), null);
    }

    public ResultadoComandoVisao evacuarComQuedaDoLider(String operador) {
        int lider = cliente.consultarComVotacao().liderId();
        if (lider <= 0) {
            lider = cliente.liderConhecido();
        }
        String preparacao = cliente.falharNoProximoComando(lider);
        return ResultadoComandoVisao.de(cliente.executar(TipoComando.acionarEvacuacao, operador,
                "Demonstração: líder c" + lider + " cai após replicar e antes de responder"), preparacao);
    }
}
