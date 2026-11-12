package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioAuditoria;
import br.sd.barragem.controlador.dominio.RegistroAuditoria;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class Auditoria {

    private static final Logger log = LoggerFactory.getLogger(Auditoria.class);

    private final RepositorioAuditoria repositorio;
    private final int meuId;

    public Auditoria(RepositorioAuditoria repositorio, VisaoCluster visao) {
        this.repositorio = repositorio;
        this.meuId = visao.meuId();
    }

    public void registrar(String tipo, String descricao) {
        log.warn("[{}] {}", tipo, descricao);
        repositorio.registrar(RegistroAuditoria.local(tipo, descricao, meuId));
    }

    public void registrar(RegistroAuditoria registro) {
        log.warn("[{}] {}", registro.tipo(), registro.descricao());
        repositorio.registrar(registro);
    }

    public List<RegistroAuditoria> recentes(int limite) {
        return repositorio.recentes(limite);
    }
}
