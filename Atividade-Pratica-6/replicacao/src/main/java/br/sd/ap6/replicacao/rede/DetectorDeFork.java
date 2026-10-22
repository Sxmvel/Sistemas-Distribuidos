package br.sd.ap6.replicacao.rede;

import br.sd.ap6.nucleo.dominio.Cadeia;

public final class DetectorDeFork {

    public Divergencia detectar(Cadeia cadeiaA, Cadeia cadeiaB) {
        var limite = Math.min(cadeiaA.tamanho(), cadeiaB.tamanho());
        var comuns = 0;
        while (comuns < limite && cadeiaA.bloco(comuns).hash().equals(cadeiaB.bloco(comuns).hash())) {
            comuns++;
        }
        return new Divergencia(comuns - 1, cadeiaA.desde(comuns), cadeiaB.desde(comuns));
    }
}
