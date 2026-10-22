package br.sd.ap6.integridade.validacao;

import br.sd.ap6.nucleo.dominio.Cadeia;
import java.util.ArrayList;
import java.util.List;

public final class Validador {

    public ResultadoValidacao validar(Cadeia cadeia) {
        return new ResultadoValidacao(verificar(cadeia).stream().limit(1).toList());
    }

    public ResultadoValidacao auditar(Cadeia cadeia) {
        return new ResultadoValidacao(verificar(cadeia));
    }

    private List<Falha> verificar(Cadeia cadeia) {
        var falhas = new ArrayList<Falha>();
        var blocos = cadeia.blocos();
        for (int i = 0; i < blocos.size(); i++) {
            var bloco = blocos.get(i);
            if (!bloco.hashConfere()) {
                falhas.add(new Falha(i, TipoFalha.hashInvalido));
            }
            if (i > 0 && !bloco.apontaPara(blocos.get(i - 1))) {
                falhas.add(new Falha(i, TipoFalha.ligacaoInvalida));
            }
        }
        return falhas;
    }
}
