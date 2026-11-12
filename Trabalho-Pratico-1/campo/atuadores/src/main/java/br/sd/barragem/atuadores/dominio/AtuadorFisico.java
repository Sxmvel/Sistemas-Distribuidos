package br.sd.barragem.atuadores.dominio;

import br.sd.barragem.comum.TipoAtuador;

import java.util.List;

public class AtuadorFisico {

    private final String id;
    private final TipoAtuador tipo;
    private final String local;
    private final QuorumComandos quorum;
    private String estado;
    private List<Integer> apoiadores = List.of();
    private long ultimaMudanca = System.currentTimeMillis();

    public AtuadorFisico(String id, TipoAtuador tipo, String local, QuorumComandos quorum) {
        this.id = id;
        this.tipo = tipo;
        this.local = local;
        this.quorum = quorum;
        this.estado = tipo.estadoInicial();
    }

    public boolean aplicar(QuorumComandos.Decisao decisao) {
        apoiadores = decisao.apoiadores();
        if (decisao.estado().equals(estado)) {
            return false;
        }
        estado = decisao.estado();
        ultimaMudanca = System.currentTimeMillis();
        return true;
    }

    public String id() {
        return id;
    }

    public TipoAtuador tipo() {
        return tipo;
    }

    public String local() {
        return local;
    }

    public QuorumComandos quorum() {
        return quorum;
    }

    public String estado() {
        return estado;
    }

    public List<Integer> apoiadores() {
        return apoiadores;
    }

    public long ultimaMudanca() {
        return ultimaMudanca;
    }
}
