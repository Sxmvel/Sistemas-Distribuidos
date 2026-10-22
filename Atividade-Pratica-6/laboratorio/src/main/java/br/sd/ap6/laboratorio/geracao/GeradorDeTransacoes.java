package br.sd.ap6.laboratorio.geracao;

import java.util.List;
import java.util.Random;
import java.util.stream.IntStream;

public final class GeradorDeTransacoes {

    private static final List<String> participantes = List.of("A", "B", "C", "D", "E", "F", "G", "H");
    private static final int valorMaximo = 99;

    private final Random aleatorio;

    public GeradorDeTransacoes(long semente) {
        this.aleatorio = new Random(semente);
    }

    public String proxima() {
        var total = participantes.size();
        var origem = aleatorio.nextInt(total);
        var destino = (origem + 1 + aleatorio.nextInt(total - 1)) % total;
        var valor = 1 + aleatorio.nextInt(valorMaximo);
        return participantes.get(origem) + "->" + participantes.get(destino) + ":" + valor;
    }

    public List<String> gerar(int quantidade) {
        return IntStream.range(0, quantidade).mapToObj(i -> proxima()).toList();
    }
}
