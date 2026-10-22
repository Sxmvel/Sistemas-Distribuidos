package br.sd.ap6.laboratorio;

import br.sd.ap6.laboratorio.experimentos.E01CadeiaDidatica;
import br.sd.ap6.laboratorio.experimentos.E02Avalanche;
import br.sd.ap6.laboratorio.experimentos.E03Adulteracao;
import br.sd.ap6.laboratorio.experimentos.E04Reescrita;
import br.sd.ap6.laboratorio.experimentos.E05ReplicasDivergentes;
import br.sd.ap6.laboratorio.experimentos.Experimento;
import br.sd.ap6.laboratorio.relatorio.EscritorDeEvidencias;
import br.sd.ap6.laboratorio.relatorio.RelatorioMarkdown;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.SaidaDeConsole;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.stream.Collectors;

public final class ExecutarTodos {

    private static final String cabecalho = "Arquivo gerado por `ExecutarTodos`. Não edite à mão: rode os "
            + "experimentos de novo. A semente é fixa, então duas execuções produzem os mesmos arquivos.";

    private ExecutarTodos() {
    }

    public static void main(String[] argumentos) throws IOException {
        var experimentos = List.<Experimento>of(
                new E01CadeiaDidatica(),
                new E02Avalanche(),
                new E03Adulteracao(),
                new E04Reescrita(),
                new E05ReplicasDivergentes());

        var filtro = Arrays.stream(argumentos)
                .map(argumento -> argumento.toUpperCase(Locale.ROOT))
                .collect(Collectors.toSet());
        var selecionados = filtro.isEmpty()
                ? experimentos
                : experimentos.stream().filter(e -> filtro.contains(e.id())).toList();
        if (selecionados.isEmpty()) {
            throw new IllegalArgumentException("nenhum experimento com os ids " + filtro + "; use E01 a E05");
        }

        var console = new SaidaDeConsole(System.out);
        var resultados = selecionados.stream()
                .map(Experimento::executar)
                .peek(console::imprimir)
                .toList();
        console.resumo(resultados);

        if (filtro.isEmpty()) {
            var destino = Path.of(System.getProperty("ap6.evidencias", "evidencias")).toAbsolutePath().normalize();
            var gravados = new EscritorDeEvidencias(destino, new RelatorioMarkdown(cabecalho)).gravar(resultados);
            System.out.println("  " + gravados.size() + " arquivos de evidência gravados em " + destino);
        } else {
            System.out.println("  execução parcial: a pasta de evidências não foi alterada (rode sem argumentos para regravá-la)");
        }

        var naoConfirmados = resultados.stream().filter(r -> !r.confirmado()).map(ResultadoExperimento::id).toList();
        if (!naoConfirmados.isEmpty()) {
            throw new IllegalStateException("experimentos com verificações falhando: " + naoConfirmados);
        }
    }
}
