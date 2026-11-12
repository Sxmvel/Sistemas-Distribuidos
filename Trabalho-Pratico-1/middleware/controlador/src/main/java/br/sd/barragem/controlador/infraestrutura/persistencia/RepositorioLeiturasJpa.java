package br.sd.barragem.controlador.infraestrutura.persistencia;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioLeituras;
import br.sd.barragem.controlador.dominio.Leitura;
import org.springframework.stereotype.Component;

@Component
public class RepositorioLeiturasJpa implements RepositorioLeituras {

    private final LeituraJpa jpa;

    public RepositorioLeiturasJpa(LeituraJpa jpa) {
        this.jpa = jpa;
    }

    @Override
    public void salvar(Leitura leitura) {
        jpa.save(new LeituraEntidade(leitura.sensorId(), leitura.tipo().name(), leitura.valor(), leitura.instante()));
    }
}
