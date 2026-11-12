package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.comum.TipoAtuador;
import br.sd.barragem.controlador.aplicacao.modelo.EstadoAtuadorConhecido;
import br.sd.barragem.controlador.aplicacao.modelo.RetratoEstado;
import br.sd.barragem.controlador.dominio.ModoOperacao;
import br.sd.barragem.controlador.dominio.NivelEmergencia;
import br.sd.barragem.controlador.dominio.TabelaLimites;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Component
public class Falsificador {

    private final Random aleatorio = new Random();

    public RetratoEstado falsificar(RetratoEstado real, ModoOperacao modo) {
        return modo == ModoOperacao.malicioso ? mascarar(real) : corromper(real);
    }

    public NivelEmergencia nivelFalso(NivelEmergencia real, ModoOperacao modo) {
        return modo == ModoOperacao.malicioso ? NivelEmergencia.normal : outroNivel(real);
    }

    private RetratoEstado mascarar(RetratoEstado real) {
        List<RetratoEstado.SensorRetrato> sensores = real.sensores().stream()
                .map(s -> new RetratoEstado.SensorRetrato(s.id(), s.tipo(),
                        Math.min(s.valor(), Math.round(TabelaLimites.de(s.tipo()).atencao() * 75.0) / 100.0), 0, s.instante()))
                .toList();
        List<EstadoAtuadorConhecido> atuadores = real.atuadores().stream()
                .map(a -> new EstadoAtuadorConhecido(a.id(), a.tipo(), TipoAtuador.valueOf(a.tipo()).estadoInicial(),
                        a.apoiadores(), a.instante()))
                .toList();
        return real.com(NivelEmergencia.normal, sensores, atuadores, List.of());
    }

    private RetratoEstado corromper(RetratoEstado real) {
        if (real.sensores().isEmpty() || aleatorio.nextBoolean()) {
            return real.com(outroNivel(real.nivel()), real.sensores(), real.atuadores(), real.motivos());
        }
        List<RetratoEstado.SensorRetrato> sensores = new ArrayList<>(real.sensores());
        int indice = aleatorio.nextInt(sensores.size());
        RetratoEstado.SensorRetrato alvo = sensores.get(indice);
        double fator = 1.6 + aleatorio.nextDouble() * 1.4;
        sensores.set(indice, new RetratoEstado.SensorRetrato(alvo.id(), alvo.tipo(),
                Math.round(alvo.valor() * fator * 100.0) / 100.0, alvo.severidade(), alvo.instante()));
        return real.com(real.nivel(), sensores, real.atuadores(), real.motivos());
    }

    private NivelEmergencia outroNivel(NivelEmergencia real) {
        NivelEmergencia[] niveis = NivelEmergencia.values();
        NivelEmergencia escolhido = real;
        while (escolhido == real) {
            escolhido = niveis[aleatorio.nextInt(niveis.length)];
        }
        return escolhido;
    }
}
