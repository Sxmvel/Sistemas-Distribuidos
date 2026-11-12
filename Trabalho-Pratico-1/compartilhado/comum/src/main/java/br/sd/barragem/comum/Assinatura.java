package br.sd.barragem.comum;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.HexFormat;

public final class Assinatura {

    private static final String segredoSensores = "segredo-sensores-serra-azul";
    private static final String segredoControladores = "segredo-controladores-serra-azul";

    private Assinatura() {
    }

    public static String chaveSensor(String sensorId) {
        return hmac(segredoSensores, sensorId);
    }

    public static String chaveControlador(int controladorId) {
        return hmac(segredoControladores, "c" + controladorId);
    }

    public static String hmac(String chave, String conteudo) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(chave.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(conteudo.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Falha ao calcular a assinatura HMAC", e);
        }
    }

    public static boolean confere(String chave, String conteudo, String assinatura) {
        if (assinatura == null) {
            return false;
        }
        byte[] esperada = hmac(chave, conteudo).getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(esperada, assinatura.getBytes(StandardCharsets.UTF_8));
    }
}
