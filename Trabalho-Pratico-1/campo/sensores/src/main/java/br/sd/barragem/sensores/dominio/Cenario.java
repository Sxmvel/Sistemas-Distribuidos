package br.sd.barragem.sensores.dominio;

import br.sd.barragem.comum.TipoSensor;

public enum Cenario {

    normal("Operação normal"),
    chuvaIntensa("Chuva intensa"),
    ruptura("Ruptura progressiva"),
    recuperacao("Recuperação");

    private final String descricao;

    Cenario(String descricao) {
        this.descricao = descricao;
    }

    public String descricao() {
        return descricao;
    }

    public double alvo(TipoSensor tipo, double base, double segundos) {
        return switch (this) {
            case normal, recuperacao -> base;
            case chuvaIntensa -> switch (tipo) {
                case chuva -> 70;
                case nivel -> Math.min(base + 0.6 * segundos, 91);
                case piezometro -> base + Math.min(1.5 * segundos, 70);
                case turbidez -> 120;
                case deslocamento -> 1.5;
            };
            case ruptura -> switch (tipo) {
                case chuva -> 90;
                case nivel -> Math.min(base + 8 + 0.35 * segundos, 99);
                case piezometro -> Math.min(base + 2.0 * segundos, base + 190);
                case turbidez -> Math.min(30 + 15 * segundos, 1500);
                case deslocamento -> Math.min(0.3 * Math.exp(segundos / 15.0), 40);
            };
        };
    }

    public static Cenario porNome(String nome) {
        for (Cenario cenario : values()) {
            if (cenario.name().equalsIgnoreCase(nome)) {
                return cenario;
            }
        }
        throw new IllegalArgumentException("Cenário desconhecido: " + nome);
    }
}
