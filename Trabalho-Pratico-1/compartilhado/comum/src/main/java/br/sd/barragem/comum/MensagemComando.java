package br.sd.barragem.comum;

public record MensagemComando(String atuadorId, String estado, int controlador, long instante, String assinatura) {

    public String conteudoAssinado() {
        return atuadorId + "|" + estado + "|" + controlador + "|" + instante;
    }

    public MensagemComando assinada() {
        return new MensagemComando(atuadorId, estado, controlador, instante,
                Assinatura.hmac(Assinatura.chaveControlador(controlador), conteudoAssinado()));
    }

    public boolean autentica() {
        return Assinatura.confere(Assinatura.chaveControlador(controlador), conteudoAssinado(), assinatura);
    }
}
