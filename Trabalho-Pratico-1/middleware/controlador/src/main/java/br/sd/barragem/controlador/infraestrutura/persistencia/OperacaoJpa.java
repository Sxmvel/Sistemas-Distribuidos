package br.sd.barragem.controlador.infraestrutura.persistencia;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface OperacaoJpa extends JpaRepository<OperacaoEntidade, Long> {

    Optional<OperacaoEntidade> findFirstByRequisicaoId(String requisicaoId);

    List<OperacaoEntidade> findBySeqGreaterThanOrderBySeqAsc(Long seq);

    Optional<OperacaoEntidade> findTopByOrderBySeqDesc();
}
