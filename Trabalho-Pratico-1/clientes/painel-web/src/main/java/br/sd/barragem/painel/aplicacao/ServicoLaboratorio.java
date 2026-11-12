package br.sd.barragem.painel.aplicacao;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.comum.MensagemSimulacao;
import br.sd.barragem.contrato.Modo;
import br.sd.barragem.painel.aplicacao.porta.GerenciadorProcessos;
import br.sd.barragem.painel.aplicacao.porta.SimuladorCampo;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class ServicoLaboratorio {

    private final ClienteBarragem cliente;
    private final SimuladorCampo simulador;
    private final GerenciadorProcessos processos;
    private final Map<Integer, String> modos = new ConcurrentHashMap<>();
    private volatile String cenario = "normal";

    public ServicoLaboratorio(ClienteBarragem cliente, SimuladorCampo simulador, GerenciadorProcessos processos) {
        this.cliente = cliente;
        this.simulador = simulador;
        this.processos = processos;
    }

    public String alterarCenario(String nome) {
        simulador.enviar(MensagemSimulacao.alterarCenario, nome);
        cenario = nome;
        return "Cenário alterado para " + nome;
    }

    public String injetarForjada() {
        simulador.enviar(MensagemSimulacao.leituraForjada, "PZ-01");
        return "Leitura forjada (HMAC inválido) injetada em PZ-01";
    }

    public String injetarPico(String sensorId) {
        simulador.enviar(MensagemSimulacao.picoSensor, sensorId);
        return "Pico espúrio injetado em " + sensorId;
    }

    public String definirModo(int id, String modo) {
        String mensagem = cliente.definirModo(id, Modo.valueOf(modo));
        modos.put(id, modo);
        return mensagem;
    }

    public String desligar(int id) {
        String mensagem = cliente.desligar(id);
        modos.remove(id);
        return mensagem;
    }

    public String religar(int id) {
        processos.iniciarControlador(id);
        modos.remove(id);
        return "Iniciando c" + id + " (leva alguns segundos)";
    }

    public String modo(int id) {
        return modos.getOrDefault(id, "honesto");
    }

    public String cenario() {
        return cenario;
    }

    public void registrarCenario(String nome) {
        cenario = nome;
    }
}
