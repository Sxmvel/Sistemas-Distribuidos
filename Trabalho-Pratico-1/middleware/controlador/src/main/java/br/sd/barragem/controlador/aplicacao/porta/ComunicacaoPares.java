package br.sd.barragem.controlador.aplicacao.porta;

import br.sd.barragem.controlador.aplicacao.modelo.PedidoOperador;
import br.sd.barragem.controlador.aplicacao.modelo.RespostaPar;
import br.sd.barragem.controlador.aplicacao.modelo.ResultadoComando;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.TipoOperacao;

import java.util.List;
import java.util.Optional;

public interface ComunicacaoPares {

    Optional<RespostaPar> ping(int parId);

    boolean replicar(int parId, Operacao operacao);

    List<Operacao> sincronizar(int parId, long desdeSeq);

    ResultadoComando encaminhar(int liderId, TipoOperacao tipo, PedidoOperador pedido);
}
