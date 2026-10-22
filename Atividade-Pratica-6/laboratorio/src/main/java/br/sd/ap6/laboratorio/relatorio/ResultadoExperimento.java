package br.sd.ap6.laboratorio.relatorio;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public record ResultadoExperimento(
        String id,
        String titulo,
        String objetivo,
        String manipulacao,
        String esperado,
        String obtido,
        List<Tabela> tabelas,
        List<Verificacao> verificacoes,
        List<String> observacoes,
        List<String> log,
        List<Diagrama> diagramas,
        List<Anexo> anexos) {

    public ResultadoExperimento {
        tabelas = List.copyOf(tabelas);
        verificacoes = List.copyOf(verificacoes);
        observacoes = List.copyOf(observacoes);
        log = List.copyOf(log);
        diagramas = List.copyOf(diagramas);
        anexos = List.copyOf(anexos);
    }

    public static Construtor de(String id, String titulo) {
        return new Construtor(id, titulo);
    }

    public long aprovadas() {
        return verificacoes.stream().filter(Verificacao::aprovada).count();
    }

    public boolean confirmado() {
        return !verificacoes.isEmpty() && aprovadas() == verificacoes.size();
    }

    public String arquivoDeLog() {
        return id.toLowerCase(Locale.ROOT) + ".log";
    }

    public static final class Construtor {

        private final String id;
        private final String titulo;
        private String objetivo = "";
        private String manipulacao = "";
        private String esperado = "";
        private String obtido = "";
        private final List<Tabela> tabelas = new ArrayList<>();
        private final List<Verificacao> verificacoes = new ArrayList<>();
        private final List<String> observacoes = new ArrayList<>();
        private final List<String> log = new ArrayList<>();
        private final List<Diagrama> diagramas = new ArrayList<>();
        private final List<Anexo> anexos = new ArrayList<>();

        private Construtor(String id, String titulo) {
            this.id = id;
            this.titulo = titulo;
        }

        public Construtor objetivo(String texto) {
            objetivo = texto;
            return this;
        }

        public Construtor manipulacao(String texto) {
            manipulacao = texto;
            return this;
        }

        public Construtor esperado(String texto) {
            esperado = texto;
            return this;
        }

        public Construtor obtido(String texto) {
            obtido = texto;
            return this;
        }

        public Construtor tabela(Tabela tabela) {
            tabelas.add(tabela);
            return this;
        }

        public Construtor verificar(String descricao, boolean condicao) {
            verificacoes.add(new Verificacao(descricao, condicao));
            return this;
        }

        public Construtor observacao(String texto) {
            observacoes.add(texto);
            return this;
        }

        public Construtor log(String linha) {
            log.add(linha);
            return this;
        }

        public Construtor diagrama(Diagrama diagrama) {
            diagramas.add(diagrama);
            return this;
        }

        public Construtor anexo(String arquivo, String conteudo) {
            anexos.add(new Anexo(arquivo, conteudo));
            return this;
        }

        public ResultadoExperimento construir() {
            return new ResultadoExperimento(id, titulo, objetivo, manipulacao, esperado, obtido,
                    tabelas, verificacoes, observacoes, log, diagramas, anexos);
        }
    }
}
