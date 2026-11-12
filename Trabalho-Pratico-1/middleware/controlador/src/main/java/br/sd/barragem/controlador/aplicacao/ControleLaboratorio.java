package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.dominio.ModoOperacao;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Random;
import java.util.concurrent.atomic.AtomicBoolean;

@Component
public class ControleLaboratorio {

    private static final Logger log = LoggerFactory.getLogger(ControleLaboratorio.class);

    private final AtomicBoolean falharNoProximoComando = new AtomicBoolean();
    private final Random aleatorio = new Random();
    private volatile ModoOperacao modo = ModoOperacao.honesto;

    public ModoOperacao modo() {
        return modo;
    }

    public void definirModo(ModoOperacao novo) {
        modo = novo;
        log.error("LABORATÓRIO: controlador agora opera em modo {}", novo.name().toUpperCase());
    }

    public boolean mentirAgora() {
        return switch (modo) {
            case honesto -> false;
            case malicioso -> true;
            case intermitente -> aleatorio.nextDouble() < 0.45;
        };
    }

    public void armarFalha() {
        falharNoProximoComando.set(true);
        log.error("LABORATÓRIO: vou cair logo depois de replicar o próximo comando, antes de responder ao cliente");
    }

    public boolean consumirFalha() {
        return falharNoProximoComando.getAndSet(false);
    }
}
