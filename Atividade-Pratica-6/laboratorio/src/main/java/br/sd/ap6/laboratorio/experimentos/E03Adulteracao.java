package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.integridade.adulteracao.Atacante;
import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.laboratorio.relatorio.Formato;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.Tabela;
import br.sd.ap6.nucleo.dominio.Cadeia;
import java.util.List;

public final class E03Adulteracao implements Experimento {

    private static final List<Integer> posicoes = List.of(1, 5, 12, 23);
    private static final int posicaoDetalhada = 5;
    private static final String valorFraudado = "1000";

    private final Validador validador = new Validador();
    private final Atacante atacante = new Atacante();

    @Override
    public String id() {
        return "E03";
    }

    @Override
    public String titulo() {
        return "Adulteração de bloco antigo e intermediário";
    }

    @Override
    public ResultadoExperimento executar() {
        var referencia = CadeiaDeReferencia.gerar();
        var resultado = ResultadoExperimento.de(id(), titulo())
                .objetivo("Verificar se a validação local detecta a alteração de um bloco já encadeado e "
                        + "registrar qual parte da cadeia é afetada.")
                .manipulacao("Valor da transação trocado para " + valorFraudado + " nos blocos " + posicoes
                        + ", sem recalcular nenhum hash (como `cadeia[1].dados = ...` no PDF).")
                .esperado("validar() acusa \"hash inválido\" exatamente no bloco alterado; nenhum outro bloco "
                        + "é acusado.");

        var tabela = new Tabela("Adulteração por posição", "Bloco", "Original", "Adulterado",
                "Hash armazenado", "Hash recalculado", "validar()", "Blocos acusados na auditoria");
        for (var posicao : posicoes) {
            var original = referencia.bloco(posicao).dados();
            var fraude = CadeiaDeReferencia.comValor(original, valorFraudado);
            var adulterada = atacante.alterarDados(referencia, posicao, fraude);
            var bloco = adulterada.bloco(posicao);
            var validacao = validador.validar(adulterada);
            var auditoria = validador.auditar(adulterada);
            tabela.linha(posicao, original, fraude, Formato.curto(bloco.hash()), Formato.curto(bloco.calcularHash()),
                    validacao.mensagem(), auditoria.blocosAfetados());
            resultado.log(String.format("bloco %02d | %-9s -> %-9s | armazenado=%s | recalculado=%s | %s | auditoria=%s",
                    posicao, original, fraude, bloco.hash(), bloco.calcularHash(), validacao.mensagem(),
                    auditoria.blocosAfetados()));
            resultado.verificar("bloco " + posicao + ": validar() responde \"hash inválido no bloco " + posicao + "\"",
                    validacao.mensagem().equals("hash inválido no bloco " + posicao));
            resultado.verificar("bloco " + posicao + ": auditoria acusa só o bloco " + posicao,
                    auditoria.blocosAfetados().equals(List.of(posicao)));
        }
        resultado.tabela(tabela);
        resultado.tabela(estadoAoRedor(referencia, posicaoDetalhada));
        resultado.verificar("a cadeia de referência continua válida (a adulteração gerou uma cópia)",
                validador.validar(referencia).valida());

        return resultado
                .obtido("as 4 adulterações foram detectadas, cada uma exatamente no bloco alterado; "
                        + "os blocos seguintes continuaram ligados.")
                .observacao("A detecção é local: basta recalcular o hash do bloco e comparar com o armazenado. "
                        + "Não é preciso consultar outra réplica.")
                .observacao("O impacto fica restrito ao bloco alterado porque o atacante não trocou o hash "
                        + "armazenado; o bloco seguinte continua apontando para esse hash, então a ligação "
                        + "segue íntegra. A falha só se espalha quando o atacante tenta esconder a fraude (E04).")
                .observacao("A posição não muda o resultado: um bloco antigo (1) é detectado da mesma forma que "
                        + "um recente (23). O custo de esconder a fraude, sim, depende da posição.")
                .construir();
    }

    private Tabela estadoAoRedor(Cadeia referencia, int posicao) {
        var fraude = CadeiaDeReferencia.comValor(referencia.bloco(posicao).dados(), valorFraudado);
        var adulterada = atacante.alterarDados(referencia, posicao, fraude);
        var tabela = new Tabela("Estado de cada bloco depois de adulterar o bloco " + posicao,
                "Bloco", "Dados", "Hash confere", "Liga no anterior");
        for (int i = posicao - 2; i <= posicao + 3; i++) {
            var bloco = adulterada.bloco(i);
            tabela.linha(i, bloco.dados(), Formato.simOuNao(bloco.hashConfere()),
                    Formato.simOuNao(bloco.apontaPara(adulterada.bloco(i - 1))));
        }
        return tabela;
    }
}
