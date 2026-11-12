package br.sd.barragem.painel.entrada.web;

import br.sd.barragem.painel.aplicacao.ServicoMonitoramento;
import br.sd.barragem.painel.aplicacao.modelo.VisaoPainel;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Component
public class FluxoSse {

    private final ServicoMonitoramento monitoramento;
    private final List<SseEmitter> emissores = new CopyOnWriteArrayList<>();

    public FluxoSse(ServicoMonitoramento monitoramento) {
        this.monitoramento = monitoramento;
    }

    public SseEmitter registrar() {
        SseEmitter emissor = new SseEmitter(0L);
        emissor.onCompletion(() -> emissores.remove(emissor));
        emissor.onTimeout(() -> emissores.remove(emissor));
        emissor.onError(erro -> emissores.remove(emissor));
        emissores.add(emissor);
        enviar(emissor, monitoramento.ultima());
        return emissor;
    }

    @Scheduled(fixedDelay = 1000, initialDelay = 1000)
    public void transmitir() {
        VisaoPainel visao = monitoramento.atualizar();
        emissores.forEach(emissor -> enviar(emissor, visao));
    }

    private void enviar(SseEmitter emissor, VisaoPainel visao) {
        try {
            emissor.send(SseEmitter.event().name("estado").data(visao));
        } catch (IOException | IllegalStateException e) {
            emissores.remove(emissor);
        }
    }
}
