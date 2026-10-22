package br.sd.ap6.nucleo.cripto;

import java.util.Map;
import java.util.StringJoiner;
import java.util.TreeMap;

public final class SerializadorCanonico {

    private SerializadorCanonico() {
    }

    public static String serializar(Map<String, ?> campos) {
        var json = new StringJoiner(", ", "{", "}");
        new TreeMap<String, Object>(campos)
                .forEach((chave, valor) -> json.add(texto(chave) + ": " + valor(valor)));
        return json.toString();
    }

    private static String valor(Object valor) {
        return switch (valor) {
            case null -> "null";
            case String texto -> texto(texto);
            case Integer inteiro -> inteiro.toString();
            case Long longo -> longo.toString();
            case Boolean logico -> logico ? "true" : "false";
            default -> throw new IllegalArgumentException(
                    "tipo sem forma canônica: " + valor.getClass().getSimpleName());
        };
    }

    private static String texto(String texto) {
        var saida = new StringBuilder(texto.length() + 2).append('"');
        for (char caractere : texto.toCharArray()) {
            switch (caractere) {
                case '"' -> saida.append("\\\"");
                case '\\' -> saida.append("\\\\");
                case '\n' -> saida.append("\\n");
                case '\r' -> saida.append("\\r");
                case '\t' -> saida.append("\\t");
                case '\b' -> saida.append("\\b");
                case '\f' -> saida.append("\\f");
                default -> {
                    if (caractere < 0x20 || caractere > 0x7e) {
                        saida.append(String.format("\\u%04x", (int) caractere));
                    } else {
                        saida.append(caractere);
                    }
                }
            }
        }
        return saida.append('"').toString();
    }
}
