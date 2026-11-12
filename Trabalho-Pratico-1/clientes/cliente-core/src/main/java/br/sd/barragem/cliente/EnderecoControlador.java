package br.sd.barragem.cliente;

import java.util.List;

public record EnderecoControlador(int id, String host, int porta) {

    public static List<EnderecoControlador> padrao() {
        return List.of(
                new EnderecoControlador(1, "localhost", 50051),
                new EnderecoControlador(2, "localhost", 50052),
                new EnderecoControlador(3, "localhost", 50053));
    }
}
