package br.sd.barragem.controlador.infraestrutura.persistencia;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "operacao")
public class OperacaoEntidade {

    @Id
    private Long seq;

    @Column(nullable = false)
    private String requisicaoId;

    private String tipo;
    private String operador;

    @Column(length = 500)
    private String motivo;

    private long instante;
    private int liderId;

    protected OperacaoEntidade() {
    }

    public OperacaoEntidade(Long seq, String requisicaoId, String tipo, String operador, String motivo,
                            long instante, int liderId) {
        this.seq = seq;
        this.requisicaoId = requisicaoId;
        this.tipo = tipo;
        this.operador = operador;
        this.motivo = motivo;
        this.instante = instante;
        this.liderId = liderId;
    }

    public Long getSeq() {
        return seq;
    }

    public String getRequisicaoId() {
        return requisicaoId;
    }

    public String getTipo() {
        return tipo;
    }

    public String getOperador() {
        return operador;
    }

    public String getMotivo() {
        return motivo;
    }

    public long getInstante() {
        return instante;
    }

    public int getLiderId() {
        return liderId;
    }
}
