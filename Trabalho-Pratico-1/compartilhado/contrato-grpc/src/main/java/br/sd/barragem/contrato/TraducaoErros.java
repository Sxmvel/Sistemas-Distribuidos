package br.sd.barragem.contrato;

import io.grpc.Status;
import io.grpc.StatusRuntimeException;

import java.util.Locale;

public final class TraducaoErros {

    private TraducaoErros() {
    }

    public static String codigo(Status.Code codigo) {
        return switch (codigo) {
            case UNAVAILABLE -> "INDISPONÍVEL";
            case DEADLINE_EXCEEDED -> "TEMPO ESGOTADO";
            case CANCELLED -> "CANCELADO";
            case INVALID_ARGUMENT -> "ARGUMENTO INVÁLIDO";
            case INTERNAL -> "ERRO INTERNO";
            case UNIMPLEMENTED -> "NÃO IMPLEMENTADO";
            case FAILED_PRECONDITION -> "PRÉ-CONDIÇÃO NÃO ATENDIDA";
            case NOT_FOUND -> "NÃO ENCONTRADO";
            case PERMISSION_DENIED, UNAUTHENTICATED -> "ACESSO NEGADO";
            case RESOURCE_EXHAUSTED -> "RECURSO ESGOTADO";
            case ABORTED -> "ABORTADO";
            default -> "FALHA";
        };
    }

    public static String descrever(StatusRuntimeException erro) {
        return descrever(erro.getStatus());
    }

    public static String descrever(Status status) {
        return codigo(status.getCode()) + ": " + detalhe(status);
    }

    private static String detalhe(Status status) {
        String descricao = status.getDescription();
        if (descricao == null || descricao.isBlank()) {
            return padrao(status.getCode());
        }
        String minusculo = descricao.toLowerCase(Locale.ROOT);
        if (minusculo.contains("io exception") || minusculo.contains("connection refused")
                || minusculo.contains("network closed") || minusculo.contains("connection reset")
                || minusculo.contains("unable to resolve") || minusculo.contains("no route")) {
            return "conexão recusada ou interrompida — réplica fora do ar";
        }
        if (minusculo.contains("deadline")) {
            return "a réplica não respondeu dentro do prazo";
        }
        if (minusculo.contains("cancelled") || minusculo.contains("canceled")) {
            return "chamada cancelada";
        }
        if (minusculo.contains("channel shutdown") || minusculo.contains("shutdown")) {
            return "canal de comunicação encerrado";
        }
        return descricao;
    }

    private static String padrao(Status.Code codigo) {
        return switch (codigo) {
            case UNAVAILABLE -> "réplica fora do ar ou inalcançável";
            case DEADLINE_EXCEEDED -> "a réplica não respondeu dentro do prazo";
            case CANCELLED -> "chamada cancelada";
            default -> "falha na comunicação com a réplica";
        };
    }
}
