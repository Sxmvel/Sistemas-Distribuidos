package br.sd.ap6.nucleo.dominio;

import br.sd.ap6.nucleo.cripto.SerializadorCanonico;
import br.sd.ap6.nucleo.cripto.Sha256;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

public record Bloco(int indice, String dados, String hashAnterior, String hash) {

    public static final String hashNulo = "0".repeat(64);
    public static final String dadosDaGenese = "genesis";

    public Bloco {
        if (indice < 0) {
            throw new IllegalArgumentException("índice negativo: " + indice);
        }
        Objects.requireNonNull(dados, "dados");
        Objects.requireNonNull(hashAnterior, "hashAnterior");
        Objects.requireNonNull(hash, "hash");
    }

    public static Bloco novo(int indice, String dados, String hashAnterior) {
        return new Bloco(indice, dados, hashAnterior, calcularHash(indice, dados, hashAnterior));
    }

    public static Bloco genese() {
        return novo(0, dadosDaGenese, hashNulo);
    }

    public String calcularHash() {
        return calcularHash(indice, dados, hashAnterior);
    }

    public boolean hashConfere() {
        return hash.equals(calcularHash());
    }

    public boolean apontaPara(Bloco anterior) {
        return hashAnterior.equals(anterior.hash());
    }

    public Bloco comDadosAdulterados(String novosDados) {
        return new Bloco(indice, novosDados, hashAnterior, hash);
    }

    public Bloco resselado() {
        return novo(indice, dados, hashAnterior);
    }

    public Bloco religadoA(String novoHashAnterior) {
        return novo(indice, dados, novoHashAnterior);
    }

    public Map<String, Object> conteudo() {
        return conteudo(indice, dados, hashAnterior);
    }

    public String formaCanonica() {
        return SerializadorCanonico.serializar(conteudo());
    }

    private static Map<String, Object> conteudo(int indice, String dados, String hashAnterior) {
        var campos = new LinkedHashMap<String, Object>();
        campos.put("indice", indice);
        campos.put("dados", dados);
        campos.put("hash_anterior", hashAnterior);
        return campos;
    }

    private static String calcularHash(int indice, String dados, String hashAnterior) {
        return Sha256.hex(SerializadorCanonico.serializar(conteudo(indice, dados, hashAnterior)));
    }
}
