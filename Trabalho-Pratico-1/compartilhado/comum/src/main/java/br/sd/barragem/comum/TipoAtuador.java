package br.sd.barragem.comum;

import java.util.List;

public enum TipoAtuador {

    sirene(List.of("desligada", "tocando")),
    painelRota(List.of("livre", "atencao", "preparar", "evacuar")),
    cancela(List.of("aberta", "fechada")),
    bomba(List.of("desligada", "ligada"));

    private final List<String> estados;

    TipoAtuador(List<String> estados) {
        this.estados = estados;
    }

    public List<String> estados() {
        return estados;
    }

    public String estadoInicial() {
        return estados.get(0);
    }

    public boolean aceita(String estado) {
        return estados.contains(estado);
    }
}
