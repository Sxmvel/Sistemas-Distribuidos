package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;

public interface Experimento {

    String id();

    String titulo();

    ResultadoExperimento executar();
}
