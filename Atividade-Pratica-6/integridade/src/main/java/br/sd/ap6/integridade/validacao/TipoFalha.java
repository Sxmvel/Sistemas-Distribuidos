package br.sd.ap6.integridade.validacao;

public enum TipoFalha {

    hashInvalido("hash inválido"),
    ligacaoInvalida("ligação inválida");

    private final String descricao;

    TipoFalha(String descricao) {
        this.descricao = descricao;
    }

    public String descricao() {
        return descricao;
    }
}
