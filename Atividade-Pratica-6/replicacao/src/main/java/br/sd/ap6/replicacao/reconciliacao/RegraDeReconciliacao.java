package br.sd.ap6.replicacao.reconciliacao;

import br.sd.ap6.nucleo.dominio.Cadeia;

public interface RegraDeReconciliacao {

    String nome();

    Escolha escolher(Cadeia cadeiaA, Cadeia cadeiaB);
}
