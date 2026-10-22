package br.sd.ap6.nucleo.dominio;

import java.util.ArrayList;
import java.util.List;

public final class Cadeia {

    private final List<Bloco> blocos;

    private Cadeia(List<Bloco> blocos) {
        if (blocos.isEmpty()) {
            throw new IllegalArgumentException("uma cadeia precisa de pelo menos o bloco gênese");
        }
        this.blocos = List.copyOf(blocos);
    }

    public static Cadeia comGenese() {
        return new Cadeia(List.of(Bloco.genese()));
    }

    public static Cadeia de(List<Bloco> blocos) {
        return new Cadeia(blocos);
    }

    public Cadeia anexar(String dados) {
        return comBloco(Bloco.novo(tamanho(), dados, ponta().hash()));
    }

    public Cadeia anexarTodos(List<String> dados) {
        var resultado = this;
        for (var dado : dados) {
            resultado = resultado.anexar(dado);
        }
        return resultado;
    }

    public Cadeia comBloco(Bloco bloco) {
        var novos = new ArrayList<>(blocos);
        novos.add(bloco);
        return new Cadeia(novos);
    }

    public Cadeia substituir(int indice, Bloco bloco) {
        var novos = new ArrayList<>(blocos);
        novos.set(indice, bloco);
        return new Cadeia(novos);
    }

    public Cadeia prefixo(int tamanho) {
        return new Cadeia(blocos.subList(0, tamanho));
    }

    public List<Bloco> desde(int indice) {
        return blocos.subList(Math.min(indice, blocos.size()), blocos.size());
    }

    public Bloco bloco(int indice) {
        return blocos.get(indice);
    }

    public Bloco ponta() {
        return blocos.getLast();
    }

    public int tamanho() {
        return blocos.size();
    }

    public List<Bloco> blocos() {
        return blocos;
    }

    @Override
    public boolean equals(Object outro) {
        return outro instanceof Cadeia cadeia && blocos.equals(cadeia.blocos);
    }

    @Override
    public int hashCode() {
        return blocos.hashCode();
    }

    @Override
    public String toString() {
        return "Cadeia[" + tamanho() + " blocos, ponta=" + ponta().hash() + "]";
    }
}
