package br.sd.barragem.controlador.dominio;

public record RegistroAuditoria(long seq, long instante, String tipo, String descricao, String origem) {

    public static RegistroAuditoria local(String tipo, String descricao, int controlador) {
        return new RegistroAuditoria(0, System.currentTimeMillis(), tipo, descricao, "c" + controlador);
    }
}
