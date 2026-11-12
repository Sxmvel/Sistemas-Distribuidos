package br.sd.barragem.painel.aplicacao.modelo;

import java.util.List;

public record VisaoPainel(long instante, String barragem, String nivel, String nivelRotulo, boolean quorum,
                          int votosNoNivel, int totalReplicas, int liderId, boolean evacuacaoManual,
                          boolean alarmeReconhecido, long descartadas, long ultimoSeq, List<String> motivos,
                          List<ControladorVisao> controladores, List<SensorVisao> sensores,
                          List<AtuadorVisao> atuadores, List<EventoVisao> eventos, String cenario) {

    public record ControladorVisao(int id, boolean respondeu, String nivel, String nivelRotulo,
                                   List<String> divergencias, String erro, boolean lider, String modo,
                                   List<Integer> quarentenadoPor, long ultimoSeq) {
    }

    public record SensorVisao(String id, String tipo, String descricao, String local, double valor,
                              String unidade, int severidade, List<Double> limiares) {
    }

    public record AtuadorVisao(String id, String tipo, String local, String estado, List<String> apoiadores) {
    }

    public record EventoVisao(long instante, String tipo, String origem, long seq, String descricao) {
    }
}
