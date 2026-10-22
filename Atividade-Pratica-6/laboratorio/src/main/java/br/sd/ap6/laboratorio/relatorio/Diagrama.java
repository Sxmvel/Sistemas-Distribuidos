package br.sd.ap6.laboratorio.relatorio;

import java.util.List;

public record Diagrama(
        String arquivo,
        String titulo,
        List<Caixa> tronco,
        Ramo superior,
        Ramo inferior,
        List<String> legenda) {

    public Diagrama {
        tronco = List.copyOf(tronco);
        legenda = List.copyOf(legenda);
    }
}
