package br.sd.barragem.controlador.aplicacao;

public class IndisponivelException extends RuntimeException {

    public IndisponivelException(String mensagem) {
        super(mensagem);
    }
}
