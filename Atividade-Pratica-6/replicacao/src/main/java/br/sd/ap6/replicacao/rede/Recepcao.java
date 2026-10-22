package br.sd.ap6.replicacao.rede;

import br.sd.ap6.nucleo.dominio.Bloco;

public record Recepcao(Bloco bloco, boolean aceito, String motivo) {

    static Recepcao aceita(Bloco bloco) {
        return new Recepcao(bloco, true, "aceito");
    }

    static Recepcao recusada(Bloco bloco, String motivo) {
        return new Recepcao(bloco, false, motivo);
    }
}
