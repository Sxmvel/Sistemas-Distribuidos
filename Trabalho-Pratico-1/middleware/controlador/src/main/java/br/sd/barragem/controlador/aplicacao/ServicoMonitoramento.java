package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.porta.RepositorioLeituras;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.Leitura;
import br.sd.barragem.controlador.dominio.VerificadorPlausibilidade;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Locale;
import java.util.Optional;

@Service
public class ServicoMonitoramento {

    private final EstadoBarragem estado;
    private final VerificadorPlausibilidade verificador;
    private final RepositorioLeituras leituras;
    private final Auditoria auditoria;
    private final int rejeicoesParaRecalibrar;

    public ServicoMonitoramento(EstadoBarragem estado, VerificadorPlausibilidade verificador,
                                RepositorioLeituras leituras, Auditoria auditoria,
                                @Value("${controlador.rejeicoes-para-recalibrar:5}") int rejeicoesParaRecalibrar) {
        this.estado = estado;
        this.verificador = verificador;
        this.leituras = leituras;
        this.auditoria = auditoria;
        this.rejeicoesParaRecalibrar = rejeicoesParaRecalibrar;
    }

    public void processar(Leitura leitura) {
        long agora = System.currentTimeMillis();
        Optional<String> problema = verificador.problema(estado.ultima(leitura.sensorId()), leitura, agora);
        if (problema.isPresent()) {
            int seguidas = estado.registrarRejeicao(leitura.sensorId());
            auditoria.registrar("leitura_descartada", leitura.sensorId() + ": " + problema.get());
            if (seguidas >= rejeicoesParaRecalibrar) {
                estado.reiniciarSensor(leitura.sensorId());
                auditoria.registrar("sensor_recalibrado", leitura.sensorId() + ": " + seguidas
                        + " rejeições seguidas — histórico reiniciado a partir da próxima leitura");
            }
            return;
        }
        leituras.salvar(leitura);
        estado.registrar(leitura, agora).ifPresent(mudanca -> auditoria.registrar("nivel",
                "Nível automático " + mudanca.de().rotulo() + " → " + mudanca.para().rotulo()
                        + (mudanca.motivos().isEmpty() ? "" : " | " + String.join("; ", mudanca.motivos()))));
    }

    public void rejeitarAssinatura(String sensorId, double valor) {
        estado.contarDescarte();
        auditoria.registrar("assinatura_invalida", String.format(Locale.ROOT,
                "Leitura de %s (valor %.1f) com assinatura HMAC inválida — descartada", sensorId, valor));
    }
}
