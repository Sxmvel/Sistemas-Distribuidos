package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.porta.PublicadorComandos;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.NivelEmergencia;
import br.sd.barragem.controlador.dominio.PoliticaAtuadores;
import org.springframework.stereotype.Service;

@Service
public class ServicoAtuacao {

    private final EstadoBarragem estado;
    private final PoliticaAtuadores politica;
    private final PublicadorComandos publicador;
    private final ControleLaboratorio laboratorio;
    private final Falsificador falsificador;

    public ServicoAtuacao(EstadoBarragem estado, PoliticaAtuadores politica, PublicadorComandos publicador,
                          ControleLaboratorio laboratorio, Falsificador falsificador) {
        this.estado = estado;
        this.politica = politica;
        this.publicador = publicador;
        this.laboratorio = laboratorio;
        this.falsificador = falsificador;
    }

    public void publicarComandos() {
        NivelEmergencia nivel = estado.nivelEfetivo();
        if (laboratorio.mentirAgora()) {
            nivel = falsificador.nivelFalso(nivel, laboratorio.modo());
        }
        politica.estadosDesejados(nivel).forEach(publicador::publicar);
    }
}
