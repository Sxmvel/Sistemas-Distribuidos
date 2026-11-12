package br.sd.barragem.controlador.infraestrutura.persistencia;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AuditoriaJpa extends JpaRepository<AuditoriaEntidade, Long> {

    List<AuditoriaEntidade> findAllByOrderByIdDesc(Pageable pagina);
}
