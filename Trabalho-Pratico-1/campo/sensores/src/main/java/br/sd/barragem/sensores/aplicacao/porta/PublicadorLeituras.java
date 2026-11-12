package br.sd.barragem.sensores.aplicacao.porta;

import br.sd.barragem.sensores.dominio.LeituraGerada;

public interface PublicadorLeituras {

    void publicar(LeituraGerada leitura);

    void publicarCenario(String cenario);
}
