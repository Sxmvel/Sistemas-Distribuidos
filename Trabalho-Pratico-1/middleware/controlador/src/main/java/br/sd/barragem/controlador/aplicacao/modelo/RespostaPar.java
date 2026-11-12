package br.sd.barragem.controlador.aplicacao.modelo;

import br.sd.barragem.controlador.dominio.NivelEmergencia;

public record RespostaPar(int id, NivelEmergencia nivel, long ultimoSeq) {
}
