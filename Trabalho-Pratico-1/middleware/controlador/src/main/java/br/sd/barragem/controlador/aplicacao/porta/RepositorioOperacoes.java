package br.sd.barragem.controlador.aplicacao.porta;

import br.sd.barragem.controlador.dominio.Operacao;

import java.util.List;
import java.util.Optional;

public interface RepositorioOperacoes {

    void salvar(Operacao operacao);

    Optional<Operacao> porRequisicao(String requisicaoId);

    List<Operacao> desde(long seq);

    long ultimoSeq();
}
