package br.sd.barragem.comum;

import java.util.Locale;

public record MensagemLeitura(String sensorId, String tipo, double valor, String unidade,
                              long instante, long sequencia, String assinatura) {

    public String conteudoAssinado() {
        return String.format(Locale.ROOT, "%s|%s|%.4f|%d|%d", sensorId, tipo, valor, instante, sequencia);
    }

    public MensagemLeitura assinada(String chave) {
        return new MensagemLeitura(sensorId, tipo, valor, unidade, instante, sequencia,
                Assinatura.hmac(chave, conteudoAssinado()));
    }

    public boolean autentica() {
        return Assinatura.confere(Assinatura.chaveSensor(sensorId), conteudoAssinado(), assinatura);
    }
}
