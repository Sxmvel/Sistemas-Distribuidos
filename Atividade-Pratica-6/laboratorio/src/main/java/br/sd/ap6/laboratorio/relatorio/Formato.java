package br.sd.ap6.laboratorio.relatorio;

import java.util.Locale;

public final class Formato {

    private static final Locale portugues = Locale.of("pt", "BR");
    private static final int digitosDoHashCurto = 12;

    private Formato() {
    }

    public static String curto(String hash) {
        return hash.length() <= digitosDoHashCurto ? hash : hash.substring(0, digitosDoHashCurto) + "…";
    }

    public static String percentual(double fracao) {
        return String.format(portugues, "%.1f%%", fracao * 100);
    }

    public static String decimal(double valor) {
        return String.format(portugues, "%.1f", valor);
    }

    public static String simOuNao(boolean valor) {
        return valor ? "sim" : "não";
    }
}
