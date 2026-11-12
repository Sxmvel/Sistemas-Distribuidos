package br.sd.barragem.controlador.dominio;

import br.sd.barragem.comum.TipoSensor;

public record Leitura(String sensorId, TipoSensor tipo, double valor, long instante) {
}
