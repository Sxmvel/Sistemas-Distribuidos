package br.sd.ap6.replicacao.reconciliacao;

import br.sd.ap6.nucleo.dominio.Cadeia;

public final class CadeiaMaisLongaVence implements RegraDeReconciliacao {

    @Override
    public String nome() {
        return "cadeia válida mais longa vence; empate decidido pelo menor hash da ponta";
    }

    @Override
    public Escolha escolher(Cadeia cadeiaA, Cadeia cadeiaB) {
        if (cadeiaA.tamanho() != cadeiaB.tamanho()) {
            var maisLonga = cadeiaA.tamanho() > cadeiaB.tamanho() ? cadeiaA : cadeiaB;
            var maisCurta = maisLonga == cadeiaA ? cadeiaB : cadeiaA;
            return new Escolha(maisLonga,
                    "mais longa (" + maisLonga.tamanho() + " contra " + maisCurta.tamanho() + " blocos)");
        }
        var menorHash = cadeiaA.ponta().hash().compareTo(cadeiaB.ponta().hash()) <= 0 ? cadeiaA : cadeiaB;
        return new Escolha(menorHash,
                "empate em " + cadeiaA.tamanho() + " blocos; vence o menor hash da ponta");
    }
}
