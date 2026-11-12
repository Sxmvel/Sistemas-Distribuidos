package br.sd.barragem.controlador.aplicacao;

public class LacunaException extends RuntimeException {

    public LacunaException(long esperado, long recebido) {
        super("esperava a operação " + esperado + " mas recebeu " + recebido);
    }
}
