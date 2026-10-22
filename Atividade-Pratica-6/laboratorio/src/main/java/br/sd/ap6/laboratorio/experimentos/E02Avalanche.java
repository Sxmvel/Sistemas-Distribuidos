package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.integridade.adulteracao.Atacante;
import br.sd.ap6.laboratorio.relatorio.Formato;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.Tabela;
import br.sd.ap6.nucleo.cripto.DistanciaDeBits;
import br.sd.ap6.nucleo.cripto.Sha256;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.nucleo.dominio.Cadeia;
import java.util.ArrayList;
import java.util.IntSummaryStatistics;
import java.util.List;

public final class E02Avalanche implements Experimento {

    private static final int totalDeBits = 256;
    private static final double limiteInferiorDaMedia = 0.46;
    private static final double limiteSuperiorDaMedia = 0.54;
    private static final double fracaoMinimaPorAmostra = 0.25;
    private static final int blocoDaPropagacao = 10;

    private final Atacante atacante = new Atacante();

    @Override
    public String id() {
        return "E02";
    }

    @Override
    public String titulo() {
        return "Efeito avalanche: alterar 1 caractere";
    }

    @Override
    public ResultadoExperimento executar() {
        var resultado = ResultadoExperimento.de(id(), titulo())
                .objetivo("Medir quanto o hash muda quando a entrada muda em um único caractere e como essa "
                        + "mudança se propaga pelo encadeamento.")
                .manipulacao("\"bloco A\" → \"bloco a\" (hash_demo.py do PDF); último dígito do valor de cada "
                        + "um dos 24 blocos gerados; reconstrução da cadeia a partir do bloco " + blocoDaPropagacao + ".")
                .esperado("Cerca de 50% dos 256 bits mudam, sem relação visível com a entrada; todos os hashes "
                        + "a partir do bloco alterado mudam.");

        demonstracaoDoPdf(resultado);
        var bits = amostrasDaCadeia(resultado);
        propagacao(resultado);

        var estatistica = bits.stream().mapToInt(Integer::intValue).summaryStatistics();
        var media = estatistica.getAverage() / totalDeBits;
        resultado.verificar("média de bits alterados entre 46% e 54% (" + Formato.percentual(media) + ")",
                media >= limiteInferiorDaMedia && media <= limiteSuperiorDaMedia);
        resultado.verificar("toda amostra altera mais de 25% dos bits (mínimo " + estatistica.getMin() + ")",
                estatistica.getMin() > fracaoMinimaPorAmostra * totalDeBits);
        resultado.tabela(estatisticas(bits, estatistica));

        return resultado
                .obtido("média de " + Formato.decimal(estatistica.getAverage()) + " de 256 bits ("
                        + Formato.percentual(media) + "), mínimo " + estatistica.getMin() + ", máximo "
                        + estatistica.getMax() + "; a mudança no bloco " + blocoDaPropagacao
                        + " alterou todos os hashes seguintes.")
                .observacao("Mudar um caractere troca cerca de metade dos bits, e não os bits \"vizinhos\" da "
                        + "mudança. Não há como prever o novo hash a partir do antigo, o que torna qualquer "
                        + "adulteração visível ao recalcular.")
                .observacao("A avalanche age dentro de um bloco; o encadeamento a estende para a cadeia. Como o "
                        + "hash de um bloco entra no conteúdo do seguinte, mudar um bloco muda todos os hashes "
                        + "posteriores, e nenhum anterior.")
                .construir();
    }

    private void demonstracaoDoPdf(ResultadoExperimento.Construtor resultado) {
        var hashA = Sha256.hex("bloco A");
        var hashMinusculo = Sha256.hex("bloco a");
        var bits = DistanciaDeBits.bitsDiferentes(hashA, hashMinusculo);
        var caracteres = DistanciaDeBits.caracteresDiferentes(hashA, hashMinusculo);
        resultado.tabela(new Tabela("hash_demo.py do PDF", "Entrada", "SHA-256")
                .linha("bloco A", "`" + hashA + "`")
                .linha("bloco a", "`" + hashMinusculo + "`")
                .linha("diferença", bits + " de 256 bits (" + Formato.percentual(bits / (double) totalDeBits) + "); "
                        + caracteres + " de 64 dígitos hexadecimais"));
        resultado.log("sha256(\"bloco A\") = " + hashA);
        resultado.log("sha256(\"bloco a\") = " + hashMinusculo);
        resultado.log("bits diferentes = " + bits + "/256; dígitos hexadecimais diferentes = " + caracteres + "/64");
        resultado.log("");
        resultado.verificar("\"bloco A\" e \"bloco a\" produzem hashes diferentes", !hashA.equals(hashMinusculo));
    }

    private List<Integer> amostrasDaCadeia(ResultadoExperimento.Construtor resultado) {
        var referencia = CadeiaDeReferencia.gerar();
        var tabela = new Tabela("Um caractere alterado em cada bloco gerado",
                "Bloco", "Original", "Alterado", "Hash original", "Hash alterado", "Bits diferentes", "% dos bits");
        var bits = new ArrayList<Integer>();
        resultado.log("avalanche por bloco (mesmo índice e mesmo hash_anterior, um caractere diferente)");
        for (var bloco : referencia.blocos().subList(1, referencia.tamanho())) {
            var alterado = trocarUltimoCaractere(bloco.dados());
            var hashAlterado = Bloco.novo(bloco.indice(), alterado, bloco.hashAnterior()).hash();
            var diferenca = DistanciaDeBits.bitsDiferentes(bloco.hash(), hashAlterado);
            bits.add(diferenca);
            tabela.linha(bloco.indice(), bloco.dados(), alterado, Formato.curto(bloco.hash()),
                    Formato.curto(hashAlterado), diferenca, Formato.percentual(diferenca / (double) totalDeBits));
            resultado.log(String.format("bloco %02d | %-9s -> %-9s | %s -> %s | %3d bits",
                    bloco.indice(), bloco.dados(), alterado, bloco.hash(), hashAlterado, diferenca));
        }
        resultado.tabela(tabela);
        return bits;
    }

    private Tabela estatisticas(List<Integer> bits, IntSummaryStatistics estatistica) {
        var media = estatistica.getAverage();
        var variancia = bits.stream().mapToDouble(b -> (b - media) * (b - media)).sum() / bits.size();
        return new Tabela("Resumo das " + bits.size() + " amostras", "Medida", "Bits", "% de 256")
                .linha("mínimo", estatistica.getMin(), Formato.percentual(estatistica.getMin() / (double) totalDeBits))
                .linha("média", Formato.decimal(media), Formato.percentual(media / totalDeBits))
                .linha("máximo", estatistica.getMax(), Formato.percentual(estatistica.getMax() / (double) totalDeBits))
                .linha("desvio padrão", Formato.decimal(Math.sqrt(variancia)), "—")
                .linha("esperado para hash ideal", "128 ± 8", "50,0%");
    }

    private void propagacao(ResultadoExperimento.Construtor resultado) {
        var referencia = CadeiaDeReferencia.gerar();
        var alterado = trocarUltimoCaractere(referencia.bloco(blocoDaPropagacao).dados());
        var reconstruida = atacante.fraudar(referencia, blocoDaPropagacao, alterado);
        var antes = hashesDiferentes(referencia, reconstruida, 0, blocoDaPropagacao);
        var depois = hashesDiferentes(referencia, reconstruida, blocoDaPropagacao, referencia.tamanho());
        var totalDepois = referencia.tamanho() - blocoDaPropagacao;
        resultado.tabela(new Tabela("Propagação: bloco " + blocoDaPropagacao + " alterado e cadeia reconstruída",
                "Faixa", "Hashes que mudaram")
                .linha("blocos 0 a " + (blocoDaPropagacao - 1), antes + " de " + blocoDaPropagacao)
                .linha("blocos " + blocoDaPropagacao + " a " + (referencia.tamanho() - 1), depois + " de " + totalDepois));
        resultado.log("");
        resultado.log("propagação: bloco " + blocoDaPropagacao + " \"" + referencia.bloco(blocoDaPropagacao).dados()
                + "\" -> \"" + alterado + "\"; hashes alterados antes=" + antes + ", a partir dele=" + depois);
        resultado.verificar("nenhum hash anterior ao bloco " + blocoDaPropagacao + " muda", antes == 0);
        resultado.verificar("todos os hashes a partir do bloco " + blocoDaPropagacao + " mudam", depois == totalDepois);
    }

    private static int hashesDiferentes(Cadeia a, Cadeia b, int inicio, int fim) {
        var total = 0;
        for (int i = inicio; i < fim; i++) {
            if (!a.bloco(i).hash().equals(b.bloco(i).hash())) {
                total++;
            }
        }
        return total;
    }

    static String trocarUltimoCaractere(String texto) {
        var ultimo = texto.charAt(texto.length() - 1);
        var novo = Character.isDigit(ultimo) ? (char) ('0' + (ultimo - '0' + 1) % 10) : (char) (ultimo + 1);
        return texto.substring(0, texto.length() - 1) + novo;
    }
}
