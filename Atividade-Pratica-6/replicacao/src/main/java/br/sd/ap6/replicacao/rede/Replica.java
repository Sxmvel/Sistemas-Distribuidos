package br.sd.ap6.replicacao.rede;

import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.nucleo.dominio.Cadeia;
import java.util.Objects;

public final class Replica {

    private final String nome;
    private final Validador validador = new Validador();
    private Cadeia cadeia;

    public Replica(String nome, Cadeia inicial) {
        this.nome = Objects.requireNonNull(nome, "nome");
        this.cadeia = Objects.requireNonNull(inicial, "inicial");
    }

    public Bloco produzir(String dados) {
        cadeia = cadeia.anexar(dados);
        return cadeia.ponta();
    }

    public Recepcao receber(Bloco bloco) {
        if (!bloco.hashConfere()) {
            return Recepcao.recusada(bloco, "hash do bloco " + bloco.indice() + " não confere");
        }
        if (bloco.indice() != cadeia.tamanho()) {
            return Recepcao.recusada(bloco,
                    "bloco " + bloco.indice() + " fora de ordem (esperado " + cadeia.tamanho() + ")");
        }
        if (!bloco.apontaPara(cadeia.ponta())) {
            return Recepcao.recusada(bloco, "bloco " + bloco.indice() + " não liga na ponta local");
        }
        cadeia = cadeia.comBloco(bloco);
        return Recepcao.aceita(bloco);
    }

    public void adotar(Cadeia nova) {
        var resultado = validador.validar(nova);
        if (!resultado.valida()) {
            throw new IllegalArgumentException(nome + " recusou cadeia inválida: " + resultado.mensagem());
        }
        cadeia = nova;
    }

    public String nome() {
        return nome;
    }

    public Cadeia cadeia() {
        return cadeia;
    }
}
