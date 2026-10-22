package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.laboratorio.geracao.GeradorDeTransacoes;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.nucleo.dominio.Cadeia;

final class CadeiaDeReferencia {

    static final long semente = 2026L;
    static final int blocosGerados = 24;

    private CadeiaDeReferencia() {
    }

    static Cadeia gerar() {
        return Cadeia.comGenese().anexarTodos(new GeradorDeTransacoes(semente).gerar(blocosGerados));
    }

    static GeradorDeTransacoes geradorDerivado(int deslocamento) {
        return new GeradorDeTransacoes(semente + deslocamento);
    }

    static String comValor(String transacao, String novoValor) {
        return transacao.substring(0, transacao.indexOf(':') + 1) + novoValor;
    }

    static String linhaDeLog(Bloco bloco) {
        return String.format("bloco %02d | %-9s | anterior=%s | hash=%s",
                bloco.indice(), bloco.dados(), bloco.hashAnterior(), bloco.hash());
    }
}
