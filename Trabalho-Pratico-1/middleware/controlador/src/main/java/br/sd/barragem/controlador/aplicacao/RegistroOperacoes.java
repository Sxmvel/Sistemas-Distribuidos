package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioOperacoes;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.RegistroAuditoria;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

@Component
public class RegistroOperacoes {

    private static final Logger log = LoggerFactory.getLogger(RegistroOperacoes.class);

    private final RepositorioOperacoes repositorio;
    private final EstadoBarragem estado;
    private final Auditoria auditoria;
    private long ultimoSeq;

    public RegistroOperacoes(RepositorioOperacoes repositorio, EstadoBarragem estado, Auditoria auditoria) {
        this.repositorio = repositorio;
        this.estado = estado;
        this.auditoria = auditoria;
    }

    @PostConstruct
    public synchronized void restaurar() {
        List<Operacao> salvas = repositorio.desde(0);
        salvas.forEach(estado::aplicar);
        ultimoSeq = repositorio.ultimoSeq();
        log.info("Armazenamento local restaurado: {} operações, última seq = {}", salvas.size(), ultimoSeq);
    }

    public synchronized long ultimoSeq() {
        return ultimoSeq;
    }

    public synchronized Optional<Operacao> porRequisicao(String requisicaoId) {
        return repositorio.porRequisicao(requisicaoId);
    }

    public synchronized boolean aplicar(Operacao operacao) {
        if (operacao.seq() <= ultimoSeq) {
            return false;
        }
        if (operacao.seq() != ultimoSeq + 1) {
            throw new LacunaException(ultimoSeq + 1, operacao.seq());
        }
        repositorio.salvar(operacao);
        estado.aplicar(operacao);
        ultimoSeq = operacao.seq();
        String motivo = operacao.motivo() == null || operacao.motivo().isBlank() ? "" : " — " + operacao.motivo();
        auditoria.registrar(new RegistroAuditoria(operacao.seq(), operacao.instante(), "operacao",
                operacao.tipo().descricao() + " por " + operacao.operador() + motivo, "líder c" + operacao.liderId()));
        return true;
    }

    public List<Operacao> desde(long seq) {
        return repositorio.desde(seq);
    }
}
