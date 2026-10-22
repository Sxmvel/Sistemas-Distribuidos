package br.sd.ap6.integridade.validacao;

import java.util.List;
import java.util.Optional;

public record ResultadoValidacao(List<Falha> falhas) {

    public static final String mensagemDeSucesso = "cadeia válida";

    public ResultadoValidacao {
        falhas = List.copyOf(falhas);
    }

    public boolean valida() {
        return falhas.isEmpty();
    }

    public Optional<Falha> primeiraFalha() {
        return falhas.stream().findFirst();
    }

    public String mensagem() {
        return primeiraFalha().map(Falha::mensagem).orElse(mensagemDeSucesso);
    }

    public List<Integer> blocosAfetados() {
        return falhas.stream().map(Falha::indice).distinct().toList();
    }

    public String formatoDoPython() {
        return "(" + (valida() ? "True" : "False") + ", '" + mensagem() + "')";
    }
}
