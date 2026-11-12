package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ServicoReplicacao {

    private static final Logger log = LoggerFactory.getLogger(ServicoReplicacao.class);

    private final RegistroOperacoes registro;
    private final ServicoSincronizacao sincronizacao;
    private final VisaoCluster visao;

    public ServicoReplicacao(RegistroOperacoes registro, ServicoSincronizacao sincronizacao, VisaoCluster visao) {
        this.registro = registro;
        this.sincronizacao = sincronizacao;
        this.visao = visao;
    }

    public boolean receber(Operacao operacao) {
        int lider = visao.lider();
        if (operacao.liderId() != lider) {
            log.warn("Replicação da seq {} recusada: veio de c{}, mas o líder na minha visão é c{}",
                    operacao.seq(), operacao.liderId(), lider);
            return false;
        }
        try {
            registro.aplicar(operacao);
        } catch (LacunaException e) {
            log.warn("Lacuna no log ({}); sincronizando com c{}", e.getMessage(), operacao.liderId());
            sincronizacao.alcancar(operacao.liderId());
            try {
                registro.aplicar(operacao);
            } catch (LacunaException ainda) {
                return false;
            }
        }
        return true;
    }

    public List<Operacao> desde(long seq) {
        return registro.desde(seq);
    }

    public long ultimoSeq() {
        return registro.ultimoSeq();
    }
}
