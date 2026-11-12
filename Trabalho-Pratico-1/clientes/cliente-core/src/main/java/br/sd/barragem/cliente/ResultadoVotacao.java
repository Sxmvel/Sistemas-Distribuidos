package br.sd.barragem.cliente;

import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.Nivel;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public record ResultadoVotacao(Nivel nivel, boolean quorum, int votosNoNivel, int liderId,
                               Optional<EstadoSistema> referencia, Map<String, Double> sensoresMedianos,
                               Map<Integer, Voto> votos, Map<Integer, EstadoSistema> respostas) {

    public record Voto(int controlador, boolean respondeu, Nivel nivel, List<String> divergencias, String erro) {

        public boolean confiavel() {
            return respondeu && divergencias.isEmpty();
        }
    }
}
