package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.integridade.adulteracao.Atacante;
import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.laboratorio.relatorio.Formato;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.Tabela;
import br.sd.ap6.nucleo.dominio.Cadeia;
import br.sd.ap6.replicacao.rede.DetectorDeFork;
import br.sd.ap6.replicacao.rede.TipoDivergencia;
import java.util.List;

public final class E04Reescrita implements Experimento {

    private static final int posicao = 5;
    private static final List<Integer> posicoesDeCusto = List.of(1, 5, 12, 23);
    private static final String valorFraudado = "1000";

    private final Validador validador = new Validador();
    private final Atacante atacante = new Atacante();
    private final DetectorDeFork detector = new DetectorDeFork();

    @Override
    public String id() {
        return "E04";
    }

    @Override
    public String titulo() {
        return "Reescrita: a cadeia adulterada volta a ser válida";
    }

    @Override
    public ResultadoExperimento executar() {
        var referencia = CadeiaDeReferencia.gerar();
        var fraude = CadeiaDeReferencia.comValor(referencia.bloco(posicao).dados(), valorFraudado);
        var resultado = ResultadoExperimento.de(id(), titulo())
                .objetivo("Mostrar que um atacante que controla a cópia local consegue esconder a adulteração "
                        + "recalculando os hashes, e que só uma referência externa revela a fraude.")
                .manipulacao("Bloco " + posicao + " fraudado para \"" + fraude + "\"; depois o atacante ressela "
                        + "o bloco e, por fim, recalcula todos os hashes do " + posicao + " ao "
                        + (referencia.tamanho() - 1) + ".")
                .esperado("O erro migra de \"hash inválido\" para \"ligação inválida\" e some; a cadeia reescrita "
                        + "passa na validação, mas diverge da referência a partir do bloco " + posicao + ".");

        var adulterada = atacante.alterarDados(referencia, posicao, fraude);
        var resselada = atacante.resselarBloco(adulterada, posicao);
        var reescrita = atacante.reescreverDesde(adulterada, posicao);

        var estagios = new Tabela("Estágios do ataque ao bloco " + posicao, "Estágio", "Ação do atacante",
                "Hashes recalculados", "validar()", "Auditoria", "Ponta igual à referência");
        estagio(resultado, estagios, "0", "nenhuma (referência)", 0, referencia, referencia, "cadeia válida");
        estagio(resultado, estagios, "1", "troca os dados do bloco " + posicao, 0, adulterada, referencia,
                "hash inválido no bloco " + posicao);
        estagio(resultado, estagios, "2", "recalcula só o hash do bloco " + posicao, 1, resselada, referencia,
                "ligação inválida no bloco " + (posicao + 1));
        estagio(resultado, estagios, "3", "recalcula os blocos " + posicao + " a " + (referencia.tamanho() - 1),
                referencia.tamanho() - posicao, reescrita, referencia, "cadeia válida");
        resultado.tabela(estagios);

        compararComReferencia(resultado, referencia, reescrita);
        resultado.tabela(custo(resultado, referencia));

        var divergencia = detector.detectar(referencia, reescrita);
        return resultado
                .obtido("depois de recalcular " + (referencia.tamanho() - posicao) + " hashes a cadeia fraudada "
                        + "responde \"" + validador.validar(reescrita).mensagem() + "\"; comparada à referência, "
                        + "diverge a partir do bloco " + divergencia.primeiroBlocoDivergente() + ".")
                .observacao("O hash garante que a cadeia é coerente consigo mesma, não que é a cadeia certa. "
                        + "Quem escreve a cópia local pode produzir outra história coerente.")
                .observacao("A fraude só aparece quando se compara a cópia com algo que o atacante não controla: "
                        + "outra réplica, um hash da ponta publicado antes ou um checkpoint.")
                .observacao("Para quem compara, a cadeia reescrita tem a mesma forma de um fork legítimo: um "
                        + "ancestral comum e dois ramos válidos. Decidir qual ramo vale é tarefa de um protocolo "
                        + "de consenso, não do hash.")
                .observacao("Sem prova de trabalho, recalcular é barato: o custo é um SHA-256 por bloco "
                        + "posterior, poucos microssegundos. Em redes reais é esse custo que se torna proibitivo.")
                .construir();
    }

    private void estagio(ResultadoExperimento.Construtor resultado, Tabela tabela, String numero, String acao,
                         int recalculados, Cadeia cadeia, Cadeia referencia, String mensagemEsperada) {
        var validacao = validador.validar(cadeia);
        var auditoria = validador.auditar(cadeia);
        var pontaIgual = cadeia.ponta().hash().equals(referencia.ponta().hash());
        tabela.linha(numero, acao, recalculados, validacao.mensagem(), auditoria.blocosAfetados(),
                Formato.simOuNao(pontaIgual));
        resultado.log(String.format("estágio %s | %-40s | recalculados=%2d | %-26s | ponta=%s",
                numero, acao, recalculados, validacao.mensagem(), cadeia.ponta().hash()));
        resultado.verificar("estágio " + numero + ": validar() responde \"" + mensagemEsperada + "\"",
                validacao.mensagem().equals(mensagemEsperada));
    }

    private void compararComReferencia(ResultadoExperimento.Construtor resultado, Cadeia referencia,
                                       Cadeia reescrita) {
        var tabela = new Tabela("Referência × cadeia reescrita", "Bloco", "Dados na referência",
                "Dados na reescrita", "Hash na referência", "Hash na reescrita", "Igual");
        resultado.log("");
        resultado.log("referência x reescrita");
        for (int i = posicao - 2; i < referencia.tamanho(); i++) {
            var original = referencia.bloco(i);
            var reescrito = reescrita.bloco(i);
            var igual = original.hash().equals(reescrito.hash());
            if (i <= posicao + 2 || i == referencia.tamanho() - 1) {
                tabela.linha(i, original.dados(), reescrito.dados(), Formato.curto(original.hash()),
                        Formato.curto(reescrito.hash()), Formato.simOuNao(igual));
            } else if (i == posicao + 3) {
                tabela.linha("…", "…", "…", "…", "…", "…");
            }
            resultado.log(String.format("bloco %02d | referência=%s | reescrita=%s | %s",
                    i, original.hash(), reescrito.hash(), igual ? "igual" : "diferente"));
        }
        resultado.tabela(tabela);

        var divergencia = detector.detectar(referencia, reescrita);
        resultado.log("detector de fork: ancestral comum=" + divergencia.ancestralComum() + ", ramos de "
                + divergencia.ramoA().size() + " e " + divergencia.ramoB().size() + " blocos, tipo="
                + divergencia.tipo().descricao());
        resultado.verificar("comparada à referência, a reescrita aparece como fork",
                divergencia.tipo() == TipoDivergencia.fork);
        resultado.verificar("o ancestral comum é o bloco " + (posicao - 1),
                divergencia.ancestralComum() == posicao - 1);
    }

    private Tabela custo(ResultadoExperimento.Construtor resultado, Cadeia referencia) {
        var tabela = new Tabela("Custo de esconder a fraude por posição", "Bloco fraudado",
                "Hashes a recalcular", "Cadeia reescrita é válida", "Ancestral comum com a referência");
        resultado.log("");
        for (var alvo : posicoesDeCusto) {
            var fraude = CadeiaDeReferencia.comValor(referencia.bloco(alvo).dados(), valorFraudado);
            var reescrita = atacante.fraudar(referencia, alvo, fraude);
            var valida = validador.validar(reescrita).valida();
            var ancestral = detector.detectar(referencia, reescrita).ancestralComum();
            tabela.linha(alvo, referencia.tamanho() - alvo, Formato.simOuNao(valida), ancestral);
            resultado.log(String.format("custo | bloco %02d fraudado | %2d hashes recalculados | válida=%s",
                    alvo, referencia.tamanho() - alvo, valida));
            resultado.verificar("fraude no bloco " + alvo + " reescrita passa na validação", valida);
        }
        return tabela;
    }
}
