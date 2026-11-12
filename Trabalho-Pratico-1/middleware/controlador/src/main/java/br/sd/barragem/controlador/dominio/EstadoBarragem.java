package br.sd.barragem.controlador.dominio;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public class EstadoBarragem {

    public record MudancaNivel(NivelEmergencia de, NivelEmergencia para, List<String> motivos) {
    }

    public record Fotografia(NivelEmergencia nivel, NivelEmergencia nivelAutomatico, boolean evacuacaoManual,
                             boolean alarmeReconhecido, Map<String, Leitura> ultimas,
                             Map<String, Integer> severidades, List<String> motivos, long descartadas) {
    }

    private final AvaliadorRisco avaliador;
    private final long histereseDescidaMs;
    private final Map<String, Deque<Leitura>> recentes = new LinkedHashMap<>();
    private final Map<String, Integer> rejeicoesSeguidas = new HashMap<>();
    private AvaliadorRisco.Avaliacao avaliacao = AvaliadorRisco.Avaliacao.vazia();
    private NivelEmergencia nivelAutomatico = NivelEmergencia.normal;
    private long abaixoDesde;
    private boolean evacuacaoManual;
    private boolean alarmeReconhecido;
    private long descartadas;

    public EstadoBarragem(AvaliadorRisco avaliador, long histereseDescidaMs) {
        this.avaliador = avaliador;
        this.histereseDescidaMs = histereseDescidaMs;
    }

    public synchronized Leitura ultima(String sensorId) {
        Deque<Leitura> leituras = recentes.get(sensorId);
        return leituras == null ? null : leituras.peekLast();
    }

    public synchronized int registrarRejeicao(String sensorId) {
        descartadas++;
        return rejeicoesSeguidas.merge(sensorId, 1, Integer::sum);
    }

    public synchronized void contarDescarte() {
        descartadas++;
    }

    public synchronized void reiniciarSensor(String sensorId) {
        recentes.remove(sensorId);
        rejeicoesSeguidas.remove(sensorId);
    }

    public synchronized Optional<MudancaNivel> registrar(Leitura leitura, long agora) {
        rejeicoesSeguidas.remove(leitura.sensorId());
        Deque<Leitura> fila = recentes.computeIfAbsent(leitura.sensorId(), id -> new ArrayDeque<>());
        fila.addLast(leitura);
        while (fila.size() > avaliador.persistencia()) {
            fila.removeFirst();
        }
        Map<String, List<Leitura>> copia = new LinkedHashMap<>();
        recentes.forEach((id, leituras) -> copia.put(id, new ArrayList<>(leituras)));
        avaliacao = avaliador.avaliar(copia);
        NivelEmergencia avaliado = avaliacao.nivel();

        if (avaliado.acimaDe(nivelAutomatico)) {
            return Optional.of(mudarPara(avaliado));
        }
        if (nivelAutomatico.acimaDe(avaliado)) {
            if (abaixoDesde == 0) {
                abaixoDesde = agora;
            } else if (agora - abaixoDesde >= histereseDescidaMs) {
                return Optional.of(mudarPara(avaliado));
            }
        } else {
            abaixoDesde = 0;
        }
        return Optional.empty();
    }

    private MudancaNivel mudarPara(NivelEmergencia novo) {
        NivelEmergencia anterior = nivelAutomatico;
        nivelAutomatico = novo;
        abaixoDesde = 0;
        if (novo.acimaDe(anterior)) {
            alarmeReconhecido = false;
        }
        return new MudancaNivel(anterior, novo, avaliacao.motivos());
    }

    public synchronized void aplicar(Operacao operacao) {
        switch (operacao.tipo()) {
            case acionarEvacuacao -> evacuacaoManual = true;
            case encerrarEvacuacao -> evacuacaoManual = false;
            case reconhecerAlarme -> alarmeReconhecido = true;
        }
    }

    public synchronized NivelEmergencia nivelEfetivo() {
        return evacuacaoManual ? NivelEmergencia.n3 : nivelAutomatico;
    }

    public synchronized Fotografia fotografia() {
        Map<String, Leitura> ultimas = new LinkedHashMap<>();
        recentes.forEach((id, leituras) -> {
            if (!leituras.isEmpty()) {
                ultimas.put(id, leituras.peekLast());
            }
        });
        return new Fotografia(nivelEfetivo(), nivelAutomatico, evacuacaoManual, alarmeReconhecido, ultimas,
                Map.copyOf(avaliacao.severidades()), List.copyOf(avaliacao.motivos()), descartadas);
    }
}
