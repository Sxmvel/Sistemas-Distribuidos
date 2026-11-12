package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.comum.Dispositivos;
import br.sd.barragem.controlador.aplicacao.modelo.RetratoEstado;
import br.sd.barragem.controlador.dominio.EstadoBarragem;
import br.sd.barragem.controlador.dominio.Leitura;
import br.sd.barragem.controlador.dominio.NivelEmergencia;
import br.sd.barragem.controlador.dominio.RegistroAuditoria;
import br.sd.barragem.controlador.dominio.VisaoCluster;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class ServicoConsulta {

    private final EstadoBarragem estado;
    private final VisaoCluster visao;
    private final RegistroOperacoes registro;
    private final EstadoAtuadoresConhecidos atuadores;
    private final ControleLaboratorio laboratorio;
    private final Falsificador falsificador;
    private final Auditoria auditoria;

    public ServicoConsulta(EstadoBarragem estado, VisaoCluster visao, RegistroOperacoes registro,
                           EstadoAtuadoresConhecidos atuadores, ControleLaboratorio laboratorio,
                           Falsificador falsificador, Auditoria auditoria) {
        this.estado = estado;
        this.visao = visao;
        this.registro = registro;
        this.atuadores = atuadores;
        this.laboratorio = laboratorio;
        this.falsificador = falsificador;
        this.auditoria = auditoria;
    }

    public RetratoEstado retratoParaCliente() {
        RetratoEstado real = retratoReal();
        return laboratorio.mentirAgora() ? falsificador.falsificar(real, laboratorio.modo()) : real;
    }

    public NivelEmergencia nivelParaPares() {
        NivelEmergencia real = estado.nivelEfetivo();
        return laboratorio.mentirAgora() ? falsificador.nivelFalso(real, laboratorio.modo()) : real;
    }

    public RetratoEstado retratoReal() {
        EstadoBarragem.Fotografia foto = estado.fotografia();
        List<RetratoEstado.SensorRetrato> sensores = new ArrayList<>();
        for (Dispositivos.Sensor sensor : Dispositivos.sensores) {
            Leitura leitura = foto.ultimas().get(sensor.id());
            if (leitura != null) {
                sensores.add(new RetratoEstado.SensorRetrato(sensor.id(), sensor.tipo(), leitura.valor(),
                        foto.severidades().getOrDefault(sensor.id(), 0), leitura.instante()));
            }
        }
        return new RetratoEstado(visao.meuId(), visao.lider(), foto.nivel(), foto.nivelAutomatico(),
                foto.evacuacaoManual(), foto.alarmeReconhecido(), sensores, atuadores.todos(), visao.situacao(),
                registro.ultimoSeq(), foto.descartadas(), foto.motivos(), System.currentTimeMillis());
    }

    public List<RegistroAuditoria> auditoria(int limite) {
        return auditoria.recentes(limite);
    }

    public long ultimoSeq() {
        return registro.ultimoSeq();
    }

    public List<Integer> emQuarentena() {
        return visao.emQuarentena();
    }

    public int meuId() {
        return visao.meuId();
    }
}
