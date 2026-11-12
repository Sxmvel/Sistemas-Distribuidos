package br.sd.barragem.controlador.infraestrutura.persistencia;

import org.springframework.data.jpa.repository.JpaRepository;

public interface LeituraJpa extends JpaRepository<LeituraEntidade, Long> {
}
