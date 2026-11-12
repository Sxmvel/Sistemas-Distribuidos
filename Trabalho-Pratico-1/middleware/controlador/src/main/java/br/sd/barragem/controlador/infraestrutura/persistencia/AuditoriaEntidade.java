package br.sd.barragem.controlador.infraestrutura.persistencia;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "auditoria")
public class AuditoriaEntidade {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private long seq;
    private long instante;
    private String tipo;

    @Column(length = 2000)
    private String descricao;

    private String origem;

    protected AuditoriaEntidade() {
    }

    public AuditoriaEntidade(long seq, long instante, String tipo, String descricao, String origem) {
        this.seq = seq;
        this.instante = instante;
        this.tipo = tipo;
        this.descricao = descricao;
        this.origem = origem;
    }

    public Long getId() {
        return id;
    }

    public long getSeq() {
        return seq;
    }

    public long getInstante() {
        return instante;
    }

    public String getTipo() {
        return tipo;
    }

    public String getDescricao() {
        return descricao;
    }

    public String getOrigem() {
        return origem;
    }
}
