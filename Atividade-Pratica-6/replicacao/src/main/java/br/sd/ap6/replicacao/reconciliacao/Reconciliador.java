package br.sd.ap6.replicacao.reconciliacao;

import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.replicacao.rede.DetectorDeFork;
import br.sd.ap6.replicacao.rede.Replica;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public final class Reconciliador {

    private final RegraDeReconciliacao regra;
    private final Validador validador = new Validador();
    private final DetectorDeFork detector = new DetectorDeFork();

    public Reconciliador(RegraDeReconciliacao regra) {
        this.regra = Objects.requireNonNull(regra, "regra");
    }

    public ResultadoReconciliacao reconciliar(Replica replicaA, Replica replicaB) {
        var divergencia = detector.detectar(replicaA.cadeia(), replicaB.cadeia());
        var escolha = escolher(replicaA, replicaB);
        var venceuA = escolha.vencedora().equals(replicaA.cadeia());
        var vencedora = venceuA ? replicaA : replicaB;
        var perdedora = venceuA ? replicaB : replicaA;
        var ramoVencedor = venceuA ? divergencia.ramoA() : divergencia.ramoB();
        var descartados = venceuA ? divergencia.ramoB() : divergencia.ramoA();

        replicaA.adotar(escolha.vencedora());
        replicaB.adotar(escolha.vencedora());

        return new ResultadoReconciliacao(
                regra.nome(),
                vencedora.nome(),
                perdedora.nome(),
                escolha.motivo(),
                divergencia,
                descartados,
                transacoesOrfas(descartados, ramoVencedor),
                escolha.vencedora().ponta().hash());
    }

    private Escolha escolher(Replica replicaA, Replica replicaB) {
        var validacaoA = validador.validar(replicaA.cadeia());
        var validacaoB = validador.validar(replicaB.cadeia());
        if (!validacaoA.valida() && !validacaoB.valida()) {
            throw new IllegalStateException("nenhuma das cópias é válida; não há o que reconciliar");
        }
        if (!validacaoA.valida()) {
            return new Escolha(replicaB.cadeia(),
                    "cópia de " + replicaA.nome() + " rejeitada: " + validacaoA.mensagem());
        }
        if (!validacaoB.valida()) {
            return new Escolha(replicaA.cadeia(),
                    "cópia de " + replicaB.nome() + " rejeitada: " + validacaoB.mensagem());
        }
        return regra.escolher(replicaA.cadeia(), replicaB.cadeia());
    }

    private static List<String> transacoesOrfas(List<Bloco> descartados, List<Bloco> ramoVencedor) {
        var incluidas = new ArrayList<>(ramoVencedor.stream().map(Bloco::dados).toList());
        var orfas = new ArrayList<String>();
        for (var bloco : descartados) {
            if (!incluidas.remove(bloco.dados())) {
                orfas.add(bloco.dados());
            }
        }
        return orfas;
    }
}
