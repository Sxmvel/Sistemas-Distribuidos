package br.sd.ap6.integridade.adulteracao;

import br.sd.ap6.nucleo.dominio.Cadeia;

public final class Atacante {

    public Cadeia alterarDados(Cadeia cadeia, int indice, String novosDados) {
        return cadeia.substituir(indice, cadeia.bloco(indice).comDadosAdulterados(novosDados));
    }

    public Cadeia resselarBloco(Cadeia cadeia, int indice) {
        return cadeia.substituir(indice, cadeia.bloco(indice).resselado());
    }

    public Cadeia reescreverDesde(Cadeia cadeia, int indice) {
        var reescrita = resselarBloco(cadeia, indice);
        for (int i = indice + 1; i < reescrita.tamanho(); i++) {
            var religado = reescrita.bloco(i).religadoA(reescrita.bloco(i - 1).hash());
            reescrita = reescrita.substituir(i, religado);
        }
        return reescrita;
    }

    public Cadeia fraudar(Cadeia cadeia, int indice, String novosDados) {
        return reescreverDesde(alterarDados(cadeia, indice, novosDados), indice);
    }
}
