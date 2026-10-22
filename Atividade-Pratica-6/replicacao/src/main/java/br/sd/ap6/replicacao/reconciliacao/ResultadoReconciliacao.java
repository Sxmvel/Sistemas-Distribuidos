package br.sd.ap6.replicacao.reconciliacao;

import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.replicacao.rede.Divergencia;
import java.util.List;

public record ResultadoReconciliacao(
        String regra,
        String vencedora,
        String perdedora,
        String motivo,
        Divergencia divergencia,
        List<Bloco> descartados,
        List<String> transacoesOrfas,
        String pontaFinal) {

    public ResultadoReconciliacao {
        descartados = List.copyOf(descartados);
        transacoesOrfas = List.copyOf(transacoesOrfas);
    }
}
