package br.sd.barragem.atuadores.aplicacao.porta;

import br.sd.barragem.atuadores.dominio.AtuadorFisico;

public interface PublicadorEstadoAtuador {

    void publicar(AtuadorFisico atuador);
}
