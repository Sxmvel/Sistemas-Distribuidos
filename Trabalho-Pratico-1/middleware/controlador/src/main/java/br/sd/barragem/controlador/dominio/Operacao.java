package br.sd.barragem.controlador.dominio;

public record Operacao(long seq, String requisicaoId, TipoOperacao tipo, String operador,
                       String motivo, long instante, int liderId) {
}
