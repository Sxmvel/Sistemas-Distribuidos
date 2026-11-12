package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.comum.Dispositivos;
import br.sd.barragem.controlador.aplicacao.modelo.EstadoAtuadorConhecido;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class EstadoAtuadoresConhecidos {

    private final Map<String, EstadoAtuadorConhecido> estados = new ConcurrentHashMap<>();

    public void atualizar(EstadoAtuadorConhecido estado) {
        estados.put(estado.id(), estado);
    }

    public List<EstadoAtuadorConhecido> todos() {
        return Dispositivos.atuadores.stream()
                .map(a -> estados.get(a.id()))
                .filter(Objects::nonNull)
                .toList();
    }
}
