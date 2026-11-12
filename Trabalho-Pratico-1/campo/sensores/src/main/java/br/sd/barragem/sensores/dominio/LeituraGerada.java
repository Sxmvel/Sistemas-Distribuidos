package br.sd.barragem.sensores.dominio;

import br.sd.barragem.comum.TipoSensor;

public record LeituraGerada(String sensorId, TipoSensor tipo, double valor, long sequencia,
                            long instante, boolean forjada) {
}
