package br.sd.barragem.controlador.dominio;

public enum TipoOperacao {

    acionarEvacuacao("Evacuação acionada manualmente"),
    reconhecerAlarme("Alarme reconhecido"),
    encerrarEvacuacao("Evacuação manual encerrada");

    private final String descricao;

    TipoOperacao(String descricao) {
        this.descricao = descricao;
    }

    public String descricao() {
        return descricao;
    }
}
