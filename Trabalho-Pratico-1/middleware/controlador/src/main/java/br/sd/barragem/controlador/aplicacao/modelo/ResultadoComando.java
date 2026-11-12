package br.sd.barragem.controlador.aplicacao.modelo;

public record ResultadoComando(boolean sucesso, String mensagem, long seq, int executadoPor, boolean repetida) {
}
