package br.sd.barragem.comum;

import java.util.List;

public record MensagemEstadoAtuador(String atuadorId, String tipo, String estado,
                                    List<Integer> apoiadores, long instante) {
}
