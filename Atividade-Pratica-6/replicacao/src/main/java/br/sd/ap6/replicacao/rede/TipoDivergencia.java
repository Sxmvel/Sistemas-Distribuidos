package br.sd.ap6.replicacao.rede;

public enum TipoDivergencia {

    identicas("cópias idênticas"),
    atraso("uma cópia é prefixo da outra (atraso)"),
    fork("ramos concorrentes (fork)");

    private final String descricao;

    TipoDivergencia(String descricao) {
        this.descricao = descricao;
    }

    public String descricao() {
        return descricao;
    }
}
