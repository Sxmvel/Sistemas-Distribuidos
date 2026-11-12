package br.sd.barragem.atuadores.aplicacao;

import br.sd.barragem.atuadores.aplicacao.porta.PublicadorEstadoAtuador;
import br.sd.barragem.atuadores.dominio.AtuadorFisico;
import br.sd.barragem.atuadores.dominio.QuorumComandos;
import br.sd.barragem.comum.Dispositivos;
import br.sd.barragem.comum.MensagemComando;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ServicoAtuadores {

    private static final Logger log = LoggerFactory.getLogger(ServicoAtuadores.class);

    private final Map<String, AtuadorFisico> atuadores = new LinkedHashMap<>();
    private final Map<String, Map<Integer, String>> divergenciasAvisadas = new HashMap<>();
    private final PublicadorEstadoAtuador publicador;
    private final long janelaReplayMs;

    public ServicoAtuadores(PublicadorEstadoAtuador publicador,
                            @Value("${atuadores.quorum:2}") int quorum,
                            @Value("${atuadores.validade-voto-ms:3000}") long validadeVoto,
                            @Value("${atuadores.janela-replay-ms:10000}") long janelaReplayMs) {
        this.publicador = publicador;
        this.janelaReplayMs = janelaReplayMs;
        for (Dispositivos.Atuador atuador : Dispositivos.atuadores) {
            atuadores.put(atuador.id(), new AtuadorFisico(atuador.id(), atuador.tipo(), atuador.local(),
                    new QuorumComandos(quorum, validadeVoto)));
        }
    }

    public synchronized void receber(MensagemComando comando) {
        AtuadorFisico atuador = atuadores.get(comando.atuadorId());
        if (atuador == null || !atuador.tipo().aceita(comando.estado())) {
            log.warn("Comando ignorado: {} não aceita '{}'", comando.atuadorId(), comando.estado());
            return;
        }
        long agora = System.currentTimeMillis();
        if (Math.abs(agora - comando.instante()) > janelaReplayMs) {
            log.warn("Comando REJEITADO de c{} para {}: instante fora da janela (possível replay)",
                    comando.controlador(), comando.atuadorId());
            return;
        }
        atuador.quorum().registrar(comando.controlador(), comando.estado(), agora);
    }

    public void rejeitarAssinatura(MensagemComando comando) {
        log.warn("Comando REJEITADO para {}: assinatura inválida em nome de c{}",
                comando.atuadorId(), comando.controlador());
    }

    public synchronized void reavaliar() {
        long agora = System.currentTimeMillis();
        for (AtuadorFisico atuador : atuadores.values()) {
            atuador.quorum().decidir(agora).ifPresent(decisao -> {
                String anterior = atuador.estado();
                if (atuador.aplicar(decisao)) {
                    log.warn("{} ({}, {}): {} -> {} | quórum: {}", atuador.id(), atuador.tipo(), atuador.local(),
                            anterior, decisao.estado().toUpperCase(), rotulos(decisao.apoiadores()));
                }
                avisarDivergencias(atuador, decisao.estado());
            });
            publicador.publicar(atuador);
        }
    }

    private void avisarDivergencias(AtuadorFisico atuador, String vencedor) {
        Map<Integer, String> atuais = atuador.quorum().divergentes(vencedor);
        Map<Integer, String> anteriores = divergenciasAvisadas.getOrDefault(atuador.id(), Map.of());
        atuais.forEach((controlador, pedido) -> {
            if (!pedido.equals(anteriores.get(controlador))) {
                log.warn("{}: c{} pediu '{}' mas a maioria decidiu '{}' — pedido ignorado",
                        atuador.id(), controlador, pedido, vencedor);
            }
        });
        divergenciasAvisadas.put(atuador.id(), atuais);
    }

    private static String rotulos(List<Integer> controladores) {
        return controladores.stream().map(c -> "c" + c).collect(Collectors.joining(", "));
    }
}
