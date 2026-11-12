package br.sd.barragem.cli.aplicacao;

import br.sd.barragem.cliente.ResultadoExecucao;
import br.sd.barragem.cliente.ResultadoVotacao;
import br.sd.barragem.cliente.Votacao;
import br.sd.barragem.contrato.EstadoAtuador;
import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.EventoAuditoria;
import br.sd.barragem.contrato.LeituraSensor;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.stream.Collectors;

public final class Formatador {

    private static final DateTimeFormatter hora = DateTimeFormatter.ofPattern("HH:mm:ss").withZone(ZoneId.systemDefault());

    private Formatador() {
    }

    public static String votacao(ResultadoVotacao resultado) {
        StringBuilder texto = new StringBuilder();
        texto.append("\n  NÍVEL: ").append(Votacao.rotulo(resultado.nivel()))
                .append(resultado.quorum()
                        ? "  (" + resultado.votosNoNivel() + " de " + resultado.votos().size() + " réplicas concordam)"
                        : "  (SEM MAIORIA — assumindo o nível mais grave informado)")
                .append("\n  Líder: c").append(resultado.liderId()).append("\n\n  Réplicas:\n");
        resultado.votos().values().forEach(voto -> {
            texto.append("    c").append(voto.controlador()).append(": ");
            if (!voto.respondeu()) {
                texto.append("SEM RESPOSTA (").append(voto.erro()).append(")\n");
            } else if (voto.confiavel()) {
                texto.append(Votacao.rotulo(voto.nivel())).append(" — ok\n");
            } else {
                texto.append(Votacao.rotulo(voto.nivel())).append(" — DIVERGENTE: ")
                        .append(String.join("; ", voto.divergencias())).append("\n");
            }
        });
        resultado.referencia().ifPresent(estado -> {
            texto.append("\n  Sensores (mediana das réplicas):\n");
            for (LeituraSensor sensor : estado.getSensoresList()) {
                double valor = resultado.sensoresMedianos().getOrDefault(sensor.getSensorId(), sensor.getValor());
                texto.append(String.format(Locale.ROOT, "    %-6s %-13s %9.1f %-5s %s%n", sensor.getSensorId(), sensor.getTipo(),
                        valor, sensor.getUnidade(), "*".repeat(sensor.getSeveridade())));
            }
            texto.append("\n  Atuadores:\n");
            for (EstadoAtuador atuador : estado.getAtuadoresList()) {
                texto.append(String.format("    %-6s %-11s %-10s quórum: %s%n", atuador.getAtuadorId(), atuador.getTipo(),
                        atuador.getEstado().toUpperCase(), String.join(", ", atuador.getApoiadoresList())));
            }
            texto.append("\n  Evacuação manual: ").append(estado.getEvacuacaoManual() ? "SIM" : "não")
                    .append(" | Alarme reconhecido: ").append(estado.getAlarmeReconhecido() ? "sim" : "NÃO")
                    .append(" | Leituras descartadas: ").append(estado.getLeiturasDescartadas()).append("\n");
            if (!estado.getMotivosList().isEmpty()) {
                texto.append("  Motivos:\n");
                estado.getMotivosList().forEach(m -> texto.append("    - ").append(m).append("\n"));
            }
        });
        return texto.toString();
    }

    public static String linhaFluxo(EstadoSistema estado) {
        String sensores = estado.getSensoresList().stream()
                .map(s -> String.format(Locale.ROOT, "%s=%.1f", s.getSensorId(), s.getValor()))
                .collect(Collectors.joining(" "));
        String sirenes = estado.getAtuadoresList().stream()
                .filter(a -> a.getTipo().equals("sirene"))
                .map(EstadoAtuador::getEstado)
                .findFirst().orElse("?");
        return String.format("%s [c%d] %-14s sirenes=%-9s %s", hora.format(Instant.ofEpochMilli(estado.getInstante())),
                estado.getControladorId(), Votacao.rotulo(estado.getNivel()), sirenes, sensores);
    }

    public static String execucao(ResultadoExecucao resultado) {
        StringBuilder texto = new StringBuilder("\n  Requisição ").append(resultado.requisicaoId()).append("\n");
        int numero = 1;
        for (ResultadoExecucao.Tentativa tentativa : resultado.tentativas()) {
            texto.append(String.format("    tentativa %d → c%d: %s (%d ms) %s%n", numero++, tentativa.controlador(),
                    tentativa.sucesso() ? "OK" : "FALHOU", tentativa.duracaoMs(), tentativa.detalhe()));
        }
        texto.append(resultado.resposta()
                .map(r -> "  RESULTADO: SUCESSO — " + r.getMensagem() + (r.getRepetida() ? " [deduplicada pelo id]" : ""))
                .orElse("  RESULTADO: FALHA — nenhuma réplica conseguiu executar"));
        return texto.toString();
    }

    public static String evento(EventoAuditoria evento) {
        return String.format("  %s %-20s %-10s %s%s", hora.format(Instant.ofEpochMilli(evento.getInstante())),
                evento.getTipo(), evento.getOrigem(), evento.getSeq() > 0 ? "[seq " + evento.getSeq() + "] " : "",
                evento.getDescricao());
    }
}
