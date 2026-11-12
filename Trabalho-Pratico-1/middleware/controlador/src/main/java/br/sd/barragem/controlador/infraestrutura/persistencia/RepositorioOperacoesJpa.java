package br.sd.barragem.controlador.infraestrutura.persistencia;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioOperacoes;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.TipoOperacao;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

@Component
public class RepositorioOperacoesJpa implements RepositorioOperacoes {

    private final OperacaoJpa jpa;

    public RepositorioOperacoesJpa(OperacaoJpa jpa) {
        this.jpa = jpa;
    }

    @Override
    public void salvar(Operacao operacao) {
        jpa.save(new OperacaoEntidade(operacao.seq(), operacao.requisicaoId(), operacao.tipo().name(),
                operacao.operador(), operacao.motivo(), operacao.instante(), operacao.liderId()));
    }

    @Override
    public Optional<Operacao> porRequisicao(String requisicaoId) {
        return jpa.findFirstByRequisicaoId(requisicaoId).map(RepositorioOperacoesJpa::paraDominio);
    }

    @Override
    public List<Operacao> desde(long seq) {
        return jpa.findBySeqGreaterThanOrderBySeqAsc(seq).stream().map(RepositorioOperacoesJpa::paraDominio).toList();
    }

    @Override
    public long ultimoSeq() {
        return jpa.findTopByOrderBySeqDesc().map(OperacaoEntidade::getSeq).orElse(0L);
    }

    private static Operacao paraDominio(OperacaoEntidade entidade) {
        return new Operacao(entidade.getSeq(), entidade.getRequisicaoId(), TipoOperacao.valueOf(entidade.getTipo()),
                entidade.getOperador(), entidade.getMotivo(), entidade.getInstante(), entidade.getLiderId());
    }
}
