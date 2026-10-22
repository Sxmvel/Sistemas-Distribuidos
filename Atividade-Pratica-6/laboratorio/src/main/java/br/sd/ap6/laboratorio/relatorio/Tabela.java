package br.sd.ap6.laboratorio.relatorio;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class Tabela {

    private final String titulo;
    private final List<String> colunas;
    private final List<List<String>> linhas = new ArrayList<>();

    public Tabela(String titulo, String... colunas) {
        this.titulo = titulo;
        this.colunas = List.of(colunas);
    }

    public Tabela linha(Object... valores) {
        if (valores.length != colunas.size()) {
            throw new IllegalArgumentException(
                    "a tabela '" + titulo + "' tem " + colunas.size() + " colunas, recebeu " + valores.length);
        }
        linhas.add(Arrays.stream(valores).map(String::valueOf).toList());
        return this;
    }

    public String titulo() {
        return titulo;
    }

    public List<String> colunas() {
        return colunas;
    }

    public List<List<String>> linhas() {
        return Collections.unmodifiableList(linhas);
    }
}
