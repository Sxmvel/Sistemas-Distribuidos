package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.modelo.RespostaPar;
import br.sd.barragem.controlador.aplicacao.porta.ComunicacaoPares;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class ServicoCluster {

    private final VisaoCluster visao;
    private final ComunicacaoPares pares;
    private final EstadoBarragem estado;
    private final RegistroOperacoes registro;
    private final ServicoSincronizacao sincronizacao;
    private final Auditoria auditoria;
    private int liderAnterior = -1;

    public ServicoCluster(VisaoCluster visao, ComunicacaoPares pares, EstadoBarragem estado,
                          RegistroOperacoes registro, ServicoSincronizacao sincronizacao, Auditoria auditoria) {
        this.visao = visao;
        this.pares = pares;
        this.estado = estado;
        this.registro = registro;
        this.sincronizacao = sincronizacao;
        this.auditoria = auditoria;
    }

    public synchronized void rodadaHeartbeat() {
        for (VisaoCluster.SituacaoPar par : visao.situacao()) {
            Optional<RespostaPar> resposta = pares.ping(par.id());
            Optional<VisaoCluster.Evento> evento = resposta.isPresent()
                    ? visao.registrarResposta(par.id(), resposta.get().nivel(), resposta.get().ultimoSeq())
                    : visao.registrarFalha(par.id());
            evento.ifPresent(this::registrar);
        }
        visao.avaliarDivergencias(estado.nivelEfetivo()).forEach(this::registrar);

        int lider = visao.lider();
        if (lider != liderAnterior) {
            auditoria.registrar("lideranca", "Líder agora é c" + lider + (lider == visao.meuId() ? " (este controlador)" : ""));
            liderAnterior = lider;
        }

        visao.situacao().stream()
                .filter(p -> p.vivo() && !p.quarentena() && p.ultimoSeq() > registro.ultimoSeq())
                .forEach(p -> sincronizacao.alcancar(p.id()));
    }

    private void registrar(VisaoCluster.Evento evento) {
        auditoria.registrar(evento.tipo(), evento.descricao());
    }
}
