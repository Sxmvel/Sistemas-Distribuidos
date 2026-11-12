package br.sd.barragem.controlador.infraestrutura.persistencia;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "leitura")
public class LeituraEntidade {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String sensorId;
    private String tipo;
    private double valor;
    private long instante;

    protected LeituraEntidade() {
    }

    public LeituraEntidade(String sensorId, String tipo, double valor, long instante) {
        this.sensorId = sensorId;
        this.tipo = tipo;
        this.valor = valor;
        this.instante = instante;
    }

    public Long getId() {
        return id;
    }

    public String getSensorId() {
        return sensorId;
    }

    public String getTipo() {
        return tipo;
    }

    public double getValor() {
        return valor;
    }

    public long getInstante() {
        return instante;
    }
}
