package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.integridade.adulteracao.Atacante;
import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.laboratorio.relatorio.Formato;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.Tabela;
import br.sd.ap6.nucleo.cripto.SerializadorCanonico;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.nucleo.dominio.Cadeia;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

public final class E01CadeiaDidatica implements Experimento {

    private static final List<String> transacoesDoPdf = List.of("A->B:10", "B->C:3", "C->D:1");
    private static final List<String> hashesDoPython = List.of(
            "776ebbe7ffb61b6a4b5fe534692f2334e70a07088209788e1176fc6970483ee4",
            "9bbeddfb50de6294c98d78aad6ea72c02d22720813c4eb94600d498749865972",
            "df5f4d5552ddab026eece0e0507f97897373825ba422d7f2618b577f6e3bdd65",
            "a0a5d1d2f2917cfc2d5c6909efd80897746430ea8116519aae55a1e18d57e40b");
    private static final String saidaValidaDoPython = "(True, 'cadeia válida')";
    private static final String saidaAdulteradaDoPython = "(False, 'hash inválido no bloco 1')";

    private final Validador validador = new Validador();
    private final Atacante atacante = new Atacante();

    @Override
    public String id() {
        return "E01";
    }

    @Override
    public String titulo() {
        return "Execução da cadeia didática e hashes de referência";
    }

    @Override
    public ResultadoExperimento executar() {
        var resultado = ResultadoExperimento.de(id(), titulo())
                .objetivo("Reproduzir em Java a cadeia didática do PDF com os mesmos hashes do Python e gerar "
                        + "a cadeia de referência usada por todos os outros experimentos.")
                .manipulacao("Cadeia do PDF (gênese + 3 transações); depois gênese + "
                        + CadeiaDeReferencia.blocosGerados + " transações geradas com semente "
                        + CadeiaDeReferencia.semente + ".")
                .esperado("Hashes e saídas idênticos aos do explorar_cadeia.py; cadeia de referência válida.");

        var pdf = Cadeia.comGenese().anexarTodos(transacoesDoPdf);
        reproduzirPdf(resultado, pdf);

        var referencia = CadeiaDeReferencia.gerar();
        registrarReferencia(resultado, referencia);

        var hashesIguais = IntStream.range(0, hashesDoPython.size())
                .allMatch(i -> pdf.bloco(i).hash().equals(hashesDoPython.get(i)));
        return resultado
                .obtido((hashesIguais ? "4/4 hashes iguais aos do Python" : "hashes divergentes do Python")
                        + "; cadeia de referência com " + referencia.tamanho() + " blocos, "
                        + validador.validar(referencia).mensagem() + ".")
                .observacao("A forma canônica de cada bloco é, por exemplo, `" + pdf.bloco(1).formaCanonica()
                        + "`: chaves em ordem alfabética e separadores `\", \"` e `\": \"`, exatamente como o "
                        + "`json.dumps(sort_keys=True)` do Python. Por isso os hashes coincidem byte a byte.")
                .observacao("Os hashes de referência do Python saem de `referencia/explorar_cadeia.py`, o código "
                        + "do PDF sem alteração (o comando está no README).")
                .observacao("A semente fixa torna a cadeia de referência idêntica em toda execução: o hash da "
                        + "ponta é sempre `" + referencia.ponta().hash() + "`.")
                .construir();
    }

    private void reproduzirPdf(ResultadoExperimento.Construtor resultado, Cadeia pdf) {
        var tabela = new Tabela("Cadeia do PDF: Java × Python", "Bloco", "Dados", "Hash em Java", "Hash em Python", "Iguais");
        resultado.log("cadeia didática do PDF");
        for (int i = 0; i < pdf.tamanho(); i++) {
            var bloco = pdf.bloco(i);
            var iguais = bloco.hash().equals(hashesDoPython.get(i));
            tabela.linha(i, bloco.dados(), Formato.curto(bloco.hash()), Formato.curto(hashesDoPython.get(i)),
                    Formato.simOuNao(iguais));
            resultado.log(CadeiaDeReferencia.linhaDeLog(bloco));
            resultado.verificar("hash do bloco " + i + " igual ao do Python", iguais);
        }
        resultado.tabela(tabela);

        var saidaValida = validador.validar(pdf).formatoDoPython();
        var saidaAdulterada = validador.validar(atacante.alterarDados(pdf, 1, "A->B:1000")).formatoDoPython();
        resultado.tabela(new Tabela("Saídas do roteiro do PDF", "Passo", "Python", "Java")
                .linha("print(validar(cadeia))", saidaValidaDoPython, saidaValida)
                .linha("cadeia[1].dados = \"A->B:1000\"; print(validar(cadeia))", saidaAdulteradaDoPython,
                        saidaAdulterada));
        resultado.log("validar(cadeia)                        -> " + saidaValida);
        resultado.log("validar(cadeia) após bloco 1 adulterado -> " + saidaAdulterada);
        resultado.verificar("saída da cadeia íntegra igual à do Python", saidaValida.equals(saidaValidaDoPython));
        resultado.verificar("saída da cadeia adulterada igual à do Python",
                saidaAdulterada.equals(saidaAdulteradaDoPython));
    }

    private void registrarReferencia(ResultadoExperimento.Construtor resultado, Cadeia referencia) {
        var tabela = new Tabela("Cadeia de referência (" + referencia.tamanho() + " blocos)",
                "Bloco", "Dados", "hash_anterior", "hash");
        resultado.log("");
        resultado.log("cadeia de referência (semente " + CadeiaDeReferencia.semente + ")");
        for (var bloco : referencia.blocos()) {
            tabela.linha(bloco.indice(), bloco.dados(), Formato.curto(bloco.hashAnterior()), "`" + bloco.hash() + "`");
            resultado.log(CadeiaDeReferencia.linhaDeLog(bloco));
        }
        resultado.tabela(tabela);
        resultado.verificar("pelo menos 20 blocos com dados gerados (" + (referencia.tamanho() - 1) + ")",
                referencia.tamanho() - 1 >= 20);
        resultado.verificar("cadeia de referência válida", validador.validar(referencia).valida());
        resultado.verificar("gerar a referência de novo produz a mesma cadeia",
                CadeiaDeReferencia.gerar().equals(referencia));
        resultado.anexo("cadeia-referencia.json", json(referencia));
    }

    private String json(Cadeia cadeia) {
        return cadeia.blocos().stream()
                .map(E01CadeiaDidatica::comHash)
                .map(SerializadorCanonico::serializar)
                .collect(Collectors.joining(",\n  ", "[\n  ", "\n]\n"));
    }

    private static LinkedHashMap<String, Object> comHash(Bloco bloco) {
        var campos = new LinkedHashMap<String, Object>(bloco.conteudo());
        campos.put("hash", bloco.hash());
        return campos;
    }
}
