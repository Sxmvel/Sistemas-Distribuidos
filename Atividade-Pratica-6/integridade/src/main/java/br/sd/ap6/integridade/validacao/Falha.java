package br.sd.ap6.integridade.validacao;

public record Falha(int indice, TipoFalha tipo) {

    public String mensagem() {
        return tipo.descricao() + " no bloco " + indice;
    }
}
