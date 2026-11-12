package br.sd.barragem.controlador.aplicacao.porta;

public interface PublicadorComandos {

    void publicar(String atuadorId, String estado);
}
