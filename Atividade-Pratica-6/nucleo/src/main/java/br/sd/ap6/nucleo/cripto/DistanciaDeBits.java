package br.sd.ap6.nucleo.cripto;

import java.util.HexFormat;

public final class DistanciaDeBits {

    private DistanciaDeBits() {
    }

    public static int bitsDiferentes(String hashA, String hashB) {
        var bytesA = HexFormat.of().parseHex(hashA);
        var bytesB = HexFormat.of().parseHex(hashB);
        exigirMesmoTamanho(bytesA.length, bytesB.length);
        var total = 0;
        for (int i = 0; i < bytesA.length; i++) {
            total += Integer.bitCount((bytesA[i] ^ bytesB[i]) & 0xff);
        }
        return total;
    }

    public static int caracteresDiferentes(String hashA, String hashB) {
        exigirMesmoTamanho(hashA.length(), hashB.length());
        var total = 0;
        for (int i = 0; i < hashA.length(); i++) {
            if (hashA.charAt(i) != hashB.charAt(i)) {
                total++;
            }
        }
        return total;
    }

    public static int totalDeBits(String hash) {
        return hash.length() * 4;
    }

    private static void exigirMesmoTamanho(int tamanhoA, int tamanhoB) {
        if (tamanhoA != tamanhoB) {
            throw new IllegalArgumentException("hashes de tamanhos diferentes: " + tamanhoA + " e " + tamanhoB);
        }
    }
}
