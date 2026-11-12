package br.sd.barragem.controlador.infraestrutura.persistencia;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioAuditoria;
import br.sd.barragem.controlador.dominio.RegistroAuditoria;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class RepositorioAuditoriaJpa implements RepositorioAuditoria {

    private final AuditoriaJpa jpa;

    public RepositorioAuditoriaJpa(AuditoriaJpa jpa) {
        this.jpa = jpa;
    }

    @Override
    public void registrar(RegistroAuditoria registro) {
        jpa.save(new AuditoriaEntidade(registro.seq(), registro.instante(), registro.tipo(),
                registro.descricao(), registro.origem()));
    }

    @Override
    public List<RegistroAuditoria> recentes(int limite) {
        return jpa.findAllByOrderByIdDesc(PageRequest.of(0, limite)).stream()
                .map(e -> new RegistroAuditoria(e.getSeq(), e.getInstante(), e.getTipo(), e.getDescricao(), e.getOrigem()))
                .toList();
    }
}
