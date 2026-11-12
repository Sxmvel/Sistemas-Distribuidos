package br.sd.barragem.painel.aplicacao;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.ResultadoVotacao;
import br.sd.barragem.cliente.Votacao;
import br.sd.barragem.comum.Dispositivos;
import br.sd.barragem.comum.TipoSensor;
import br.sd.barragem.contrato.EstadoPar;
import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.LeituraSensor;
import br.sd.barragem.painel.aplicacao.modelo.VisaoPainel;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class ServicoMonitoramento {

    private final ClienteBarragem cliente;
    private final ServicoLaboratorio laboratorio;
    private volatile VisaoPainel ultima;

    public ServicoMonitoramento(ClienteBarragem cliente, ServicoLaboratorio laboratorio) {
        this.cliente = cliente;
        this.laboratorio = laboratorio;
    }

    public VisaoPainel ultima() {
        return ultima == null ? atualizar() : ultima;
    }

    public synchronized VisaoPainel atualizar() {
        ResultadoVotacao votacao = cliente.consultarComVotacao();
        boolean alguemRespondeu = votacao.votos().values().stream().anyMatch(ResultadoVotacao.Voto::respondeu);
        EstadoSistema referencia = votacao.referencia().orElse(EstadoSistema.getDefaultInstance());

        List<VisaoPainel.ControladorVisao> controladores = new ArrayList<>();
        votacao.votos().values().forEach(voto -> controladores.add(new VisaoPainel.ControladorVisao(
                voto.controlador(), voto.respondeu(), voto.nivel().name(), Votacao.rotulo(voto.nivel()),
                voto.divergencias(), voto.erro(), voto.respondeu() && voto.controlador() == votacao.liderId(),
                laboratorio.modo(voto.controlador()), quemQuarentena(votacao, voto.controlador()),
                votacao.respostas().containsKey(voto.controlador())
                        ? votacao.respostas().get(voto.controlador()).getUltimoSeq() : 0)));

        List<VisaoPainel.SensorVisao> sensores = new ArrayList<>();
        for (LeituraSensor sensor : referencia.getSensoresList()) {
            TipoSensor tipo = TipoSensor.valueOf(sensor.getTipo());
            sensores.add(new VisaoPainel.SensorVisao(sensor.getSensorId(), sensor.getTipo(), tipo.descricao(),
                    Dispositivos.sensor(sensor.getSensorId()).map(Dispositivos.Sensor::local).orElse(""),
                    votacao.sensoresMedianos().getOrDefault(sensor.getSensorId(), sensor.getValor()),
                    sensor.getUnidade(), sensor.getSeveridade(), sensor.getLimiaresList()));
        }

        List<VisaoPainel.AtuadorVisao> atuadores = referencia.getAtuadoresList().stream()
                .map(a -> new VisaoPainel.AtuadorVisao(a.getAtuadorId(), a.getTipo(),
                        Dispositivos.atuador(a.getAtuadorId()).map(Dispositivos.Atuador::local).orElse(""),
                        a.getEstado(), a.getApoiadoresList()))
                .toList();

        List<VisaoPainel.EventoVisao> eventos = cliente.auditoria(40)
                .map(lista -> lista.getEventosList().stream()
                        .map(e -> new VisaoPainel.EventoVisao(e.getInstante(), e.getTipo(), e.getOrigem(), e.getSeq(), e.getDescricao()))
                        .toList())
                .orElse(List.of());

        ultima = new VisaoPainel(System.currentTimeMillis(), Dispositivos.barragem,
                alguemRespondeu ? votacao.nivel().name() : "indisponivel",
                alguemRespondeu ? Votacao.rotulo(votacao.nivel()) : "SEM RESPOSTA",
                votacao.quorum(), votacao.votosNoNivel(), votacao.votos().size(), votacao.liderId(),
                referencia.getEvacuacaoManual(), referencia.getAlarmeReconhecido(), referencia.getLeiturasDescartadas(),
                referencia.getUltimoSeq(), referencia.getMotivosList(), controladores, sensores, atuadores, eventos,
                laboratorio.cenario());
        return ultima;
    }

    private static List<Integer> quemQuarentena(ResultadoVotacao votacao, int alvo) {
        List<Integer> acusadores = new ArrayList<>();
        votacao.respostas().forEach((id, estado) -> {
            for (EstadoPar par : estado.getParesList()) {
                if (par.getId() == alvo && par.getQuarentena()) {
                    acusadores.add(id);
                }
            }
        });
        return acusadores;
    }
}
