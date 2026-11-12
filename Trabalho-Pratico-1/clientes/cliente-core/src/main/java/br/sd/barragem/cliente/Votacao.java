package br.sd.barragem.cliente;

import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.LeituraSensor;
import br.sd.barragem.contrato.Nivel;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.stream.Collectors;

public final class Votacao {

    private Votacao() {
    }

    public static ResultadoVotacao apurar(Map<Integer, EstadoSistema> respostas, Map<Integer, String> falhas, int total) {
        Map<Nivel, Long> contagem = respostas.values().stream()
                .collect(Collectors.groupingBy(EstadoSistema::getNivel, Collectors.counting()));
        Optional<Map.Entry<Nivel, Long>> maioria = contagem.entrySet().stream()
                .filter(e -> e.getValue() * 2 > total)
                .findFirst();
        boolean quorum = maioria.isPresent();
        Nivel nivel = maioria.map(Map.Entry::getKey).orElseGet(() -> contagem.keySet().stream()
                .max(Comparator.comparingInt(Nivel::getNumber)).orElse(Nivel.normal));
        int votosNoNivel = contagem.getOrDefault(nivel, 0L).intValue();

        Map<String, Double> medianas = medianas(respostas.values());
        Map<Integer, ResultadoVotacao.Voto> votos = new TreeMap<>();
        respostas.forEach((id, estado) -> {
            List<String> divergencias = new ArrayList<>();
            if (quorum && estado.getNivel() != nivel) {
                divergencias.add("informa " + rotulo(estado.getNivel()) + ", a maioria informa " + rotulo(nivel));
            }
            if (respostas.size() >= 2) {
                for (LeituraSensor sensor : estado.getSensoresList()) {
                    Double mediana = medianas.get(sensor.getSensorId());
                    if (mediana != null && Math.abs(sensor.getValor() - mediana) > tolerancia(sensor.getTipo(), mediana)) {
                        divergencias.add(String.format(Locale.ROOT, "%s = %.1f %s, mediana das réplicas = %.1f",
                                sensor.getSensorId(), sensor.getValor(), sensor.getUnidade(), mediana));
                    }
                }
            }
            votos.put(id, new ResultadoVotacao.Voto(id, true, estado.getNivel(), divergencias, ""));
        });
        falhas.forEach((id, erro) -> votos.put(id, new ResultadoVotacao.Voto(id, false, Nivel.normal, List.of(), erro)));

        int lider = respostas.values().stream()
                .filter(e -> votos.get(e.getControladorId()).confiavel())
                .collect(Collectors.groupingBy(EstadoSistema::getLiderId, Collectors.counting()))
                .entrySet().stream().max(Map.Entry.comparingByValue()).map(Map.Entry::getKey).orElse(0);

        Optional<EstadoSistema> referencia = respostas.values().stream()
                .filter(e -> votos.get(e.getControladorId()).confiavel())
                .min(Comparator.comparingInt((EstadoSistema e) -> e.getControladorId() == lider ? 0 : 1)
                        .thenComparingInt(EstadoSistema::getControladorId))
                .or(() -> respostas.values().stream().filter(e -> e.getNivel() == nivel).findFirst());

        return new ResultadoVotacao(nivel, quorum, votosNoNivel, lider, referencia, medianas, votos, new TreeMap<>(respostas));
    }

    private static Map<String, Double> medianas(java.util.Collection<EstadoSistema> estados) {
        Map<String, List<Double>> valores = new LinkedHashMap<>();
        estados.forEach(e -> e.getSensoresList().forEach(s ->
                valores.computeIfAbsent(s.getSensorId(), id -> new ArrayList<>()).add(s.getValor())));
        Map<String, Double> medianas = new HashMap<>();
        valores.forEach((id, lista) -> {
            List<Double> ordenada = lista.stream().sorted().toList();
            int meio = ordenada.size() / 2;
            medianas.put(id, ordenada.size() % 2 == 1 ? ordenada.get(meio) : (ordenada.get(meio - 1) + ordenada.get(meio)) / 2);
        });
        return medianas;
    }

    private static double tolerancia(String tipo, double mediana) {
        double absoluta = switch (tipo) {
            case "piezometro" -> 15;
            case "deslocamento" -> 1.0;
            case "nivel" -> 2;
            case "chuva" -> 10;
            case "turbidez" -> 60;
            default -> 10;
        };
        return Math.max(absoluta, Math.abs(mediana) * 0.15);
    }

    public static String rotulo(Nivel nivel) {
        return switch (nivel) {
            case normal -> "NORMAL";
            case atencao -> "ATENÇÃO";
            case n1 -> "EMERGÊNCIA N1";
            case n2 -> "EMERGÊNCIA N2";
            case n3 -> "EMERGÊNCIA N3";
            default -> "?";
        };
    }
}
