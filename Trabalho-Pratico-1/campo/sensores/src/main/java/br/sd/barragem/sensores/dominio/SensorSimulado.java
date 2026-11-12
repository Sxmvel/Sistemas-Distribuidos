package br.sd.barragem.sensores.dominio;

import br.sd.barragem.comum.TipoSensor;

import java.util.Random;

public class SensorSimulado {

    private final String id;
    private final TipoSensor tipo;
    private final double base;
    private final double taxa;
    private final double ruido;
    private double valor;
    private long sequencia;

    public SensorSimulado(String id, TipoSensor tipo, double base) {
        this.id = id;
        this.tipo = tipo;
        this.base = base;
        this.valor = base;
        this.taxa = switch (tipo) {
            case piezometro -> 6;
            case deslocamento -> 2.5;
            case nivel -> 0.8;
            case chuva -> 10;
            case turbidez -> 45;
        };
        this.ruido = switch (tipo) {
            case piezometro -> 0.8;
            case deslocamento -> 0.03;
            case nivel -> 0.08;
            case chuva -> 0.6;
            case turbidez -> 2;
        };
    }

    public LeituraGerada avancar(Cenario cenario, double segundos, Random aleatorio) {
        double alvo = cenario.alvo(tipo, base, segundos);
        double passo = Math.max(-taxa, Math.min(taxa, alvo - valor));
        valor = Math.max(0, valor + passo + aleatorio.nextGaussian() * ruido);
        return gerar(valor, false);
    }

    public LeituraGerada pico() {
        double salto = switch (tipo) {
            case piezometro -> 260;
            case deslocamento -> 60;
            case nivel -> 40;
            case chuva -> 300;
            case turbidez -> 3000;
        };
        return gerar(valor + salto, false);
    }

    public LeituraGerada forjada() {
        return gerar(base, true);
    }

    private LeituraGerada gerar(double valorPublicado, boolean forjada) {
        sequencia++;
        return new LeituraGerada(id, tipo, arredondar(valorPublicado), sequencia, System.currentTimeMillis(), forjada);
    }

    private static double arredondar(double numero) {
        return Math.round(numero * 100.0) / 100.0;
    }

    public String id() {
        return id;
    }

    public TipoSensor tipo() {
        return tipo;
    }
}
