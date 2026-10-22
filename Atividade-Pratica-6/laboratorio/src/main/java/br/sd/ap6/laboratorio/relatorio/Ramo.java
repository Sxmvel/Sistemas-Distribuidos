package br.sd.ap6.laboratorio.relatorio;

import java.util.List;

public record Ramo(String nome, String situacao, List<Caixa> caixas, boolean mantido) {

    public Ramo {
        caixas = List.copyOf(caixas);
    }
}
