package br.sd.barragem.controlador.aplicacao.modelo;

import java.util.List;

public record EstadoAtuadorConhecido(String id, String tipo, String estado, List<Integer> apoiadores, long instante) {
}
