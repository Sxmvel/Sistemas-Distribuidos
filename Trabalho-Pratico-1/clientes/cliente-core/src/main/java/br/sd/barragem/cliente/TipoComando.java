package br.sd.barragem.cliente;

public enum TipoComando {

    acionarEvacuacao("Acionar evacuação"),
    reconhecerAlarme("Reconhecer alarme"),
    encerrarEvacuacao("Encerrar evacuação manual");

    private final String descricao;

    TipoComando(String descricao) {
        this.descricao = descricao;
    }

    public String descricao() {
        return descricao;
    }
}
