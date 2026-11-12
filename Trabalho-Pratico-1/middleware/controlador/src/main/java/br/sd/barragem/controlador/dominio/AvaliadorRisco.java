package br.sd.barragem.controlador.dominio;

import br.sd.barragem.comum.TipoSensor;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.IntStream;

public class AvaliadorRisco {

    public record Avaliacao(NivelEmergencia nivel, Map<String, Integer> severidades, List<String> motivos) {

        public static Avaliacao vazia() {
            return new Avaliacao(NivelEmergencia.normal, Map.of(), List.of());
        }
    }

    private final int persistencia;

    public AvaliadorRisco(int persistencia) {
        this.persistencia = persistencia;
    }

    public int persistencia() {
        return persistencia;
    }

    public Avaliacao avaliar(Map<String, List<Leitura>> recentes) {
        Map<String, Integer> severidades = new TreeMap<>();
        Map<TipoSensor, Integer> porTipo = new EnumMap<>(TipoSensor.class);
        List<String> motivos = new ArrayList<>();
        recentes.forEach((sensorId, leituras) -> {
            if (leituras.isEmpty()) {
                return;
            }
            Leitura ultima = leituras.get(leituras.size() - 1);
            int severidade = leituras.size() < persistencia ? 0 : leituras.stream()
                    .mapToInt(l -> TabelaLimites.severidade(l.tipo(), l.valor()))
                    .min().orElse(0);
            severidades.put(sensorId, severidade);
            porTipo.merge(ultima.tipo(), severidade, Math::max);
            if (severidade > 0) {
                motivos.add(String.format(Locale.ROOT, "%s (%s) = %.1f %s — severidade %d",
                        sensorId, ultima.tipo().descricao(), ultima.valor(), ultima.tipo().unidade(), severidade));
            }
        });
        return new Avaliacao(classificar(porTipo), severidades, motivos);
    }

    private static NivelEmergencia classificar(Map<TipoSensor, Integer> porTipo) {
        int piezometro = porTipo.getOrDefault(TipoSensor.piezometro, 0);
        int deslocamento = porTipo.getOrDefault(TipoSensor.deslocamento, 0);
        int nivel = porTipo.getOrDefault(TipoSensor.nivel, 0);
        int turbidez = porTipo.getOrDefault(TipoSensor.turbidez, 0);
        int chuva = porTipo.getOrDefault(TipoSensor.chuva, 0);
        int[] estruturais = {piezometro, deslocamento, nivel, turbidez};
        int maximo = IntStream.of(estruturais).max().orElse(0);
        long criticos = IntStream.of(estruturais).filter(s -> s >= 3).count();
        long altos = IntStream.of(estruturais).filter(s -> s >= 2).count();
        long alterados = IntStream.of(estruturais).filter(s -> s >= 1).count();

        if (deslocamento >= 4 || (deslocamento >= 3 && (piezometro >= 4 || turbidez >= 4))) {
            return NivelEmergencia.n3;
        }
        if (criticos >= 2 || maximo >= 4) {
            return NivelEmergencia.n2;
        }
        if (maximo >= 3 || altos >= 2) {
            return NivelEmergencia.n1;
        }
        if (maximo >= 2 || alterados >= 2 || chuva >= 3) {
            return NivelEmergencia.atencao;
        }
        return NivelEmergencia.normal;
    }
}
