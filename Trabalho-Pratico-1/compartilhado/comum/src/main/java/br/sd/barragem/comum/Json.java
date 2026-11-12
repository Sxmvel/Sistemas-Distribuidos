package br.sd.barragem.comum;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;

public final class Json {

    private static final ObjectMapper mapeador = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    private Json() {
    }

    public static byte[] escrever(Object objeto) {
        try {
            return mapeador.writeValueAsBytes(objeto);
        } catch (IOException e) {
            throw new IllegalArgumentException("Não foi possível converter a mensagem para JSON", e);
        }
    }

    public static <T> T ler(byte[] conteudo, Class<T> tipo) {
        try {
            return mapeador.readValue(conteudo, tipo);
        } catch (IOException e) {
            throw new IllegalArgumentException("JSON inválido ou incompatível com " + tipo.getSimpleName(), e);
        }
    }
}
