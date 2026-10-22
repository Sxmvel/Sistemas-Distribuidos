package br.sd.ap6.laboratorio.relatorio;

import java.util.List;

public final class RelatorioMarkdown {

    private final String cabecalho;

    public RelatorioMarkdown(String cabecalho) {
        this.cabecalho = cabecalho;
    }

    public String gerar(List<ResultadoExperimento> resultados) {
        var md = new StringBuilder();
        md.append("# Evidências da AP6\n\n").append(cabecalho).append("\n\n");
        md.append("## Tabela de experimentos\n\n");
        md.append(tabela(resumo(resultados)));
        for (var resultado : resultados) {
            md.append(secao(resultado));
        }
        return md.toString();
    }

    private Tabela resumo(List<ResultadoExperimento> resultados) {
        var tabela = new Tabela("", "Experimento", "Manipulação", "Esperado", "Obtido", "Verificações");
        for (var r : resultados) {
            tabela.linha(r.id() + " — " + r.titulo(), r.manipulacao(), r.esperado(), r.obtido(),
                    r.aprovadas() + "/" + r.verificacoes().size() + (r.confirmado() ? " ✔" : " ✘"));
        }
        return tabela;
    }

    private String secao(ResultadoExperimento r) {
        var md = new StringBuilder("\n## ").append(r.id()).append(" — ").append(r.titulo()).append("\n\n");
        md.append("**Objetivo.** ").append(r.objetivo()).append("\n\n");
        md.append("**Manipulação.** ").append(r.manipulacao()).append("\n\n");
        md.append("**Esperado.** ").append(r.esperado()).append("\n\n");
        md.append("**Obtido.** ").append(r.obtido()).append("\n\n");
        for (var tabela : r.tabelas()) {
            md.append("### ").append(tabela.titulo()).append("\n\n").append(tabela(tabela));
        }
        for (var diagrama : r.diagramas()) {
            md.append("![").append(diagrama.titulo()).append("](").append(diagrama.arquivo()).append(")\n\n");
        }
        md.append("**Verificações**\n\n");
        for (var verificacao : r.verificacoes()) {
            md.append("- [").append(verificacao.aprovada() ? "x" : " ").append("] ")
                    .append(verificacao.descricao()).append('\n');
        }
        if (!r.observacoes().isEmpty()) {
            md.append("\n**Observações**\n\n");
            r.observacoes().forEach(observacao -> md.append("- ").append(observacao).append('\n'));
        }
        md.append("\nLog completo dos hashes: [`").append(r.arquivoDeLog()).append("`](")
                .append(r.arquivoDeLog()).append(")\n");
        r.anexos().forEach(anexo -> md.append("\nAnexo: [`").append(anexo.arquivo()).append("`](")
                .append(anexo.arquivo()).append(")\n"));
        return md.toString();
    }

    private String tabela(Tabela tabela) {
        var md = new StringBuilder();
        md.append(linha(tabela.colunas()));
        md.append(linha(tabela.colunas().stream().map(coluna -> "---").toList()));
        tabela.linhas().forEach(celulas -> md.append(linha(celulas)));
        return md.append('\n').toString();
    }

    private String linha(List<String> celulas) {
        var md = new StringBuilder("|");
        celulas.forEach(celula -> md.append(' ').append(escapar(celula)).append(" |"));
        return md.append('\n').toString();
    }

    private String escapar(String celula) {
        return celula.replace("|", "\\|").replace("\n", " ");
    }
}
