package br.sd.ap6.laboratorio.relatorio;

import java.io.PrintStream;
import java.util.List;

public final class SaidaDeConsole {

    private final PrintStream saida;

    public SaidaDeConsole(PrintStream saida) {
        this.saida = saida;
    }

    public void imprimir(ResultadoExperimento resultado) {
        saida.println();
        saida.println("=".repeat(100));
        saida.println(resultado.id() + " — " + resultado.titulo());
        saida.println("=".repeat(100));
        resultado.log().forEach(linha -> saida.println("  " + linha));
        saida.println();
        for (var verificacao : resultado.verificacoes()) {
            saida.println("  [" + (verificacao.aprovada() ? "ok" : "FALHOU") + "] " + verificacao.descricao());
        }
        saida.println("  obtido: " + resultado.obtido());
    }

    public void resumo(List<ResultadoExperimento> resultados) {
        var total = resultados.stream().mapToLong(r -> r.verificacoes().size()).sum();
        var aprovadas = resultados.stream().mapToLong(ResultadoExperimento::aprovadas).sum();
        saida.println();
        saida.println("-".repeat(100));
        for (var r : resultados) {
            saida.printf("  %-4s %-60s %3d/%-3d %s%n", r.id(), r.titulo(), r.aprovadas(), r.verificacoes().size(),
                    r.confirmado() ? "confirmado" : "NÃO CONFIRMADO");
        }
        saida.printf("  %d verificações, %d falhas%n", total, total - aprovadas);
    }
}
