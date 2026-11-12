package br.sd.barragem.atuadores.dominio;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

public class QuorumComandos {

    public record Voto(String estado, long recebidoEm) {
    }

    public record Decisao(String estado, List<Integer> apoiadores) {
    }

    private final Map<Integer, Voto> votos = new HashMap<>();
    private final int quorum;
    private final long validadeMs;

    public QuorumComandos(int quorum, long validadeMs) {
        this.quorum = quorum;
        this.validadeMs = validadeMs;
    }

    public void registrar(int controlador, String estado, long agora) {
        votos.put(controlador, new Voto(estado, agora));
    }

    public Optional<Decisao> decidir(long agora) {
        votos.values().removeIf(voto -> agora - voto.recebidoEm() > validadeMs);
        Map<String, List<Integer>> porEstado = votos.entrySet().stream()
                .collect(Collectors.groupingBy(e -> e.getValue().estado(),
                        Collectors.mapping(Map.Entry::getKey, Collectors.toList())));
        return porEstado.entrySet().stream()
                .filter(e -> e.getValue().size() >= quorum)
                .max(Map.Entry.comparingByValue((a, b) -> Integer.compare(a.size(), b.size())))
                .map(e -> new Decisao(e.getKey(), e.getValue().stream().sorted().toList()));
    }

    public Map<Integer, String> divergentes(String estadoVencedor) {
        return votos.entrySet().stream()
                .filter(e -> !e.getValue().estado().equals(estadoVencedor))
                .collect(Collectors.toMap(Map.Entry::getKey, e -> e.getValue().estado()));
    }
}
