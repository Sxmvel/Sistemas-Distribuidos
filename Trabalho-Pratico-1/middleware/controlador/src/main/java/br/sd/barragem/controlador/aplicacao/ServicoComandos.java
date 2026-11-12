package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.modelo.PedidoOperador;
import br.sd.barragem.controlador.aplicacao.modelo.ResultadoComando;
import br.sd.barragem.controlador.aplicacao.porta.ComunicacaoPares;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.TipoOperacao;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class ServicoComandos {

    private static final Logger log = LoggerFactory.getLogger(ServicoComandos.class);

    private final RegistroOperacoes registro;
    private final VisaoCluster visao;
    private final ComunicacaoPares pares;
    private final ServicoSincronizacao sincronizacao;
    private final ControleLaboratorio laboratorio;
    private final int quorum;

    public ServicoComandos(RegistroOperacoes registro, VisaoCluster visao, ComunicacaoPares pares,
                           ServicoSincronizacao sincronizacao, ControleLaboratorio laboratorio,
                           @Value("${controlador.quorum-replicacao:2}") int quorum) {
        this.registro = registro;
        this.visao = visao;
        this.pares = pares;
        this.sincronizacao = sincronizacao;
        this.laboratorio = laboratorio;
        this.quorum = quorum;
    }

    public ResultadoComando executar(TipoOperacao tipo, PedidoOperador pedido) {
        Optional<ResultadoComando> repetida = jaExecutada(pedido);
        if (repetida.isPresent()) {
            return repetida.get();
        }
        int lider = visao.lider();
        if (lider != visao.meuId()) {
            log.info("Requisição {} recebida; encaminhando ao líder c{}", pedido.requisicaoId(), lider);
            return pares.encaminhar(lider, tipo, pedido);
        }
        return executarComoLider(tipo, pedido);
    }

    public ResultadoComando executarEncaminhado(TipoOperacao tipo, PedidoOperador pedido, int origem) {
        Optional<ResultadoComando> repetida = jaExecutada(pedido);
        if (repetida.isPresent()) {
            return repetida.get();
        }
        if (!visao.souLider()) {
            throw new IndisponivelException("c" + visao.meuId() + " recebeu encaminhamento de c" + origem
                    + " mas não é o líder (líder atual: c" + visao.lider() + ")");
        }
        return executarComoLider(tipo, pedido);
    }

    private Optional<ResultadoComando> jaExecutada(PedidoOperador pedido) {
        return registro.porRequisicao(pedido.requisicaoId()).map(operacao -> {
            log.info("Requisição {} já executada (seq {}): devolvendo o resultado original", pedido.requisicaoId(), operacao.seq());
            return new ResultadoComando(true, operacao.tipo().descricao() + " (seq " + operacao.seq()
                    + ") — requisição repetida, não executada de novo", operacao.seq(), visao.meuId(), true);
        });
    }

    private synchronized ResultadoComando executarComoLider(TipoOperacao tipo, PedidoOperador pedido) {
        Optional<ResultadoComando> repetida = jaExecutada(pedido);
        if (repetida.isPresent()) {
            return repetida.get();
        }
        visao.situacao().stream()
                .filter(p -> p.vivo() && !p.quarentena() && p.ultimoSeq() > registro.ultimoSeq())
                .forEach(p -> sincronizacao.alcancar(p.id()));

        long seq = registro.ultimoSeq() + 1;
        Operacao operacao = new Operacao(seq, pedido.requisicaoId(), tipo, pedido.operador(), pedido.motivo(),
                System.currentTimeMillis(), visao.meuId());

        List<Integer> confirmaram = new ArrayList<>();
        for (int par : visao.ativos()) {
            if (pares.replicar(par, operacao)) {
                confirmaram.add(par);
            }
        }
        if (confirmaram.size() + 1 < quorum) {
            throw new IndisponivelException("sem quórum de replicação para seq " + seq
                    + ": só c" + visao.meuId() + " confirmou (mínimo " + quorum + ")");
        }
        registro.aplicar(operacao);

        if (laboratorio.consumirFalha()) {
            log.error("LABORATÓRIO: seq {} replicada em c{} — caindo AGORA, sem responder ao cliente", seq,
                    confirmaram.stream().map(String::valueOf).collect(Collectors.joining(", c")));
            Runtime.getRuntime().halt(1);
        }

        String replicas = confirmaram.stream().map(id -> "c" + id).collect(Collectors.joining(", "));
        return new ResultadoComando(true, tipo.descricao() + " (seq " + seq + ", replicada em c" + visao.meuId()
                + (replicas.isEmpty() ? "" : ", " + replicas) + ")", seq, visao.meuId(), false);
    }
}
