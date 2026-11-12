package br.sd.barragem.controlador.dominio;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.function.Function;
import java.util.stream.Collectors;

public class VisaoCluster {

    public record SituacaoPar(int id, boolean vivo, boolean quarentena, NivelEmergencia nivel,
                              long ultimoSeq, int suspeita) {
    }

    public record Evento(String tipo, String descricao) {
    }

    private static final class Par {
        private final int id;
        private boolean vivo;
        private boolean quarentena;
        private NivelEmergencia nivel = NivelEmergencia.normal;
        private long ultimoSeq;
        private int suspeita;

        private Par(int id) {
            this.id = id;
        }
    }

    private final int meuId;
    private final int limiteQuarentena;
    private final int tetoSuspeita;
    private final Map<Integer, Par> pares = new TreeMap<>();

    public VisaoCluster(int meuId, Collection<Integer> idsPares, int limiteQuarentena, int tetoSuspeita) {
        this.meuId = meuId;
        this.limiteQuarentena = limiteQuarentena;
        this.tetoSuspeita = tetoSuspeita;
        idsPares.forEach(id -> pares.put(id, new Par(id)));
    }

    public int meuId() {
        return meuId;
    }

    public synchronized Optional<Evento> registrarResposta(int id, NivelEmergencia nivel, long ultimoSeq) {
        Par par = pares.get(id);
        par.nivel = nivel;
        par.ultimoSeq = ultimoSeq;
        if (!par.vivo) {
            par.vivo = true;
            return Optional.of(new Evento("par_voltou", "c" + id + " respondeu ao heartbeat"));
        }
        return Optional.empty();
    }

    public synchronized Optional<Evento> registrarFalha(int id) {
        Par par = pares.get(id);
        if (par.vivo) {
            par.vivo = false;
            return Optional.of(new Evento("par_caiu", "c" + id + " não respondeu ao heartbeat"));
        }
        return Optional.empty();
    }

    public synchronized int lider() {
        return pares.values().stream()
                .filter(p -> p.vivo && !p.quarentena)
                .mapToInt(p -> p.id)
                .reduce(meuId, Math::min);
    }

    public synchronized boolean souLider() {
        return lider() == meuId;
    }

    public synchronized List<Integer> ativos() {
        return pares.values().stream().filter(p -> p.vivo && !p.quarentena).map(p -> p.id).toList();
    }

    public synchronized List<Integer> emQuarentena() {
        return pares.values().stream().filter(p -> p.quarentena).map(p -> p.id).toList();
    }

    public synchronized List<SituacaoPar> situacao() {
        return pares.values().stream()
                .map(p -> new SituacaoPar(p.id, p.vivo, p.quarentena, p.nivel, p.ultimoSeq, p.suspeita))
                .toList();
    }

    public synchronized List<Evento> avaliarDivergencias(NivelEmergencia meuNivel) {
        List<Evento> eventos = new ArrayList<>();
        List<Par> vivos = pares.values().stream().filter(p -> p.vivo).toList();
        for (Par par : vivos) {
            List<NivelEmergencia> outros = new ArrayList<>();
            outros.add(meuNivel);
            vivos.stream().filter(o -> o != par && !o.quarentena).forEach(o -> outros.add(o.nivel));
            Optional<NivelEmergencia> referencia = maioria(outros);
            if (outros.size() < 2 || referencia.isEmpty()) {
                continue;
            }
            if (par.nivel != referencia.get()) {
                par.suspeita = Math.min(tetoSuspeita, par.suspeita + 3);
            } else {
                par.suspeita = Math.max(0, par.suspeita - 1);
            }
            if (!par.quarentena && par.suspeita >= limiteQuarentena) {
                par.quarentena = true;
                eventos.add(new Evento("quarentena", "c" + par.id + " colocado em quarentena: informa "
                        + par.nivel.rotulo() + " enquanto a maioria informa " + referencia.get().rotulo()));
            } else if (par.quarentena && par.suspeita == 0) {
                par.quarentena = false;
                eventos.add(new Evento("liberacao", "c" + par.id + " voltou a concordar com a maioria e saiu da quarentena"));
            }
        }
        return eventos;
    }

    private static Optional<NivelEmergencia> maioria(List<NivelEmergencia> niveis) {
        return niveis.stream()
                .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()))
                .entrySet().stream()
                .filter(e -> e.getValue() * 2 > niveis.size())
                .map(Map.Entry::getKey)
                .findFirst();
    }
}
