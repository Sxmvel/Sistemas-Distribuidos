package br.sd.ap6.replicacao.rede;

import br.sd.ap6.nucleo.dominio.Bloco;
import java.util.List;

public record Divergencia(int ancestralComum, List<Bloco> ramoA, List<Bloco> ramoB) {

    public Divergencia {
        ramoA = List.copyOf(ramoA);
        ramoB = List.copyOf(ramoB);
    }

    public TipoDivergencia tipo() {
        if (ramoA.isEmpty() && ramoB.isEmpty()) {
            return TipoDivergencia.identicas;
        }
        if (ramoA.isEmpty() || ramoB.isEmpty()) {
            return TipoDivergencia.atraso;
        }
        return TipoDivergencia.fork;
    }

    public int primeiroBlocoDivergente() {
        return ancestralComum + 1;
    }
}
