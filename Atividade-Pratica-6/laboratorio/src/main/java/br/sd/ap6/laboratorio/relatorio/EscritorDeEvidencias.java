package br.sd.ap6.laboratorio.relatorio;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class EscritorDeEvidencias {

    private final Path diretorio;
    private final RelatorioMarkdown relatorio;
    private final DiagramaPng desenhista = new DiagramaPng();

    public EscritorDeEvidencias(Path diretorio, RelatorioMarkdown relatorio) {
        this.diretorio = diretorio;
        this.relatorio = relatorio;
    }

    public List<Path> gravar(List<ResultadoExperimento> resultados) throws IOException {
        Files.createDirectories(diretorio);
        limpar();
        var gravados = new ArrayList<Path>();
        gravados.add(texto("relatorio.md", relatorio.gerar(resultados)));
        for (var resultado : resultados) {
            gravados.add(texto(resultado.arquivoDeLog(), String.join("\n", resultado.log()) + "\n"));
            for (var anexo : resultado.anexos()) {
                gravados.add(texto(anexo.arquivo(), anexo.conteudo()));
            }
            for (var diagrama : resultado.diagramas()) {
                var destino = diretorio.resolve(diagrama.arquivo());
                desenhista.desenhar(diagrama, destino);
                gravados.add(destino);
            }
        }
        return gravados;
    }

    private void limpar() throws IOException {
        try (var arquivos = Files.list(diretorio)) {
            for (var arquivo : arquivos.filter(Files::isRegularFile).toList()) {
                Files.delete(arquivo);
            }
        }
    }

    private Path texto(String nome, String conteudo) throws IOException {
        var destino = diretorio.resolve(nome);
        Files.writeString(destino, conteudo, StandardCharsets.UTF_8);
        return destino;
    }
}
