package br.sd.ap6.nucleo.cripto;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

public final class Sha256 {

    private Sha256() {
    }

    public static String hex(String texto) {
        return hex(texto.getBytes(StandardCharsets.UTF_8));
    }

    public static String hex(byte[] conteudo) {
        try {
            var digest = MessageDigest.getInstance("SHA-256").digest(conteudo);
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException erro) {
            throw new IllegalStateException("SHA-256 indisponível nesta JVM", erro);
        }
    }
}
