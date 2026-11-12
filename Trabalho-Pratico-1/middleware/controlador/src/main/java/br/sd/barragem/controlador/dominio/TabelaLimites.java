package br.sd.barragem.controlador.dominio;

import br.sd.barragem.comum.TipoSensor;

public final class TabelaLimites {

    public record Limites(double atencao, double n1, double n2, double n3,
                          double minimo, double maximo, double variacaoPorSegundo) {
    }

    private TabelaLimites() {
    }

    public static Limites de(TipoSensor tipo) {
        return switch (tipo) {
            case piezometro -> new Limites(140, 170, 200, 230, 0, 600, 30);
            case deslocamento -> new Limites(1.0, 3.0, 8.0, 15.0, 0, 200, 10);
            case nivel -> new Limites(85, 90, 95, 98, 0, 110, 5);
            case chuva -> new Limites(20, 40, 60, 90, 0, 400, 60);
            case turbidez -> new Limites(100, 250, 500, 800, 0, 5000, 200);
        };
    }

    public static int severidade(TipoSensor tipo, double valor) {
        Limites limites = de(tipo);
        if (valor >= limites.n3()) {
            return 4;
        }
        if (valor >= limites.n2()) {
            return 3;
        }
        if (valor >= limites.n1()) {
            return 2;
        }
        if (valor >= limites.atencao()) {
            return 1;
        }
        return 0;
    }
}
