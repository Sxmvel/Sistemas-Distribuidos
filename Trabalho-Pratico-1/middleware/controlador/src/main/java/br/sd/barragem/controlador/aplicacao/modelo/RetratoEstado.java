package br.sd.barragem.controlador.aplicacao.modelo;

import br.sd.barragem.comum.TipoSensor;
import br.sd.barragem.controlador.dominio.NivelEmergencia;
import br.sd.barragem.controlador.dominio.VisaoCluster;

import java.util.List;

public record RetratoEstado(int controladorId, int liderId, NivelEmergencia nivel, NivelEmergencia nivelAutomatico,
                            boolean evacuacaoManual, boolean alarmeReconhecido, List<SensorRetrato> sensores,
                            List<EstadoAtuadorConhecido> atuadores, List<VisaoCluster.SituacaoPar> pares,
                            long ultimoSeq, long descartadas, List<String> motivos, long instante) {

    public record SensorRetrato(String id, TipoSensor tipo, double valor, int severidade, long instante) {
    }

    public RetratoEstado com(NivelEmergencia novoNivel, List<SensorRetrato> novosSensores,
                             List<EstadoAtuadorConhecido> novosAtuadores, List<String> novosMotivos) {
        return new RetratoEstado(controladorId, liderId, novoNivel, novoNivel, evacuacaoManual && novoNivel == NivelEmergencia.n3,
                alarmeReconhecido, novosSensores, novosAtuadores, pares, ultimoSeq, descartadas, novosMotivos, instante);
    }
}
