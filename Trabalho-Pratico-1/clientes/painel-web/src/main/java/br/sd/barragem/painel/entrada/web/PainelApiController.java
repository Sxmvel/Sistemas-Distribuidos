package br.sd.barragem.painel.entrada.web;

import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.TipoComando;
import br.sd.barragem.painel.aplicacao.ServicoLaboratorio;
import br.sd.barragem.painel.aplicacao.ServicoMonitoramento;
import br.sd.barragem.painel.aplicacao.ServicoOperacao;
import br.sd.barragem.painel.aplicacao.modelo.ResultadoComandoVisao;
import br.sd.barragem.painel.aplicacao.modelo.VisaoPainel;
import io.grpc.StatusRuntimeException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class PainelApiController {

    public record PedidoComandoWeb(String operador, String motivo) {
    }

    private static final Logger log = LoggerFactory.getLogger(PainelApiController.class);

    private final ServicoMonitoramento monitoramento;
    private final ServicoOperacao operacao;
    private final ServicoLaboratorio laboratorio;
    private final FluxoSse fluxo;

    public PainelApiController(ServicoMonitoramento monitoramento, ServicoOperacao operacao,
                               ServicoLaboratorio laboratorio, FluxoSse fluxo) {
        this.monitoramento = monitoramento;
        this.operacao = operacao;
        this.laboratorio = laboratorio;
        this.fluxo = fluxo;
    }

    @GetMapping("/estado")
    public VisaoPainel estado() {
        return monitoramento.ultima();
    }

    @GetMapping("/fluxo")
    public SseEmitter fluxo() {
        return fluxo.registrar();
    }

    @PostMapping("/comandos/{tipo}")
    public ResultadoComandoVisao comando(@PathVariable String tipo, @RequestBody(required = false) PedidoComandoWeb pedido) {
        String operador = pedido == null || pedido.operador() == null || pedido.operador().isBlank()
                ? "centro-monitoramento" : pedido.operador();
        String motivo = pedido == null ? "" : pedido.motivo();
        return operacao.executar(TipoComando.valueOf(tipo), operador, motivo);
    }

    @PostMapping("/demonstracoes/evacuar-com-queda-do-lider")
    public ResultadoComandoVisao evacuarComQueda() {
        return operacao.evacuarComQuedaDoLider("centro-monitoramento");
    }

    @PostMapping("/laboratorio/cenario/{nome}")
    public Map<String, String> cenario(@PathVariable String nome) {
        return Map.of("mensagem", laboratorio.alterarCenario(nome));
    }

    @PostMapping("/laboratorio/forjada")
    public Map<String, String> forjada() {
        return Map.of("mensagem", laboratorio.injetarForjada());
    }

    @PostMapping("/laboratorio/pico/{sensorId}")
    public Map<String, String> pico(@PathVariable String sensorId) {
        return Map.of("mensagem", laboratorio.injetarPico(sensorId));
    }

    @PostMapping("/laboratorio/controladores/{id}/modo/{modo}")
    public Map<String, String> modo(@PathVariable int id, @PathVariable String modo) {
        return Map.of("mensagem", laboratorio.definirModo(id, modo));
    }

    @PostMapping("/laboratorio/controladores/{id}/desligar")
    public Map<String, String> desligar(@PathVariable int id) {
        return Map.of("mensagem", laboratorio.desligar(id));
    }

    @PostMapping("/laboratorio/controladores/{id}/religar")
    public Map<String, String> religar(@PathVariable int id) {
        return Map.of("mensagem", laboratorio.religar(id));
    }

    @ExceptionHandler(StatusRuntimeException.class)
    public ResponseEntity<Map<String, String>> indisponivel(StatusRuntimeException e) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("mensagem", "Controlador indisponível — " + ClienteBarragem.descrever(e)));
    }

    @ExceptionHandler({IllegalArgumentException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<Map<String, String>> invalido(Exception e) {
        return ResponseEntity.badRequest()
                .body(Map.of("mensagem", "Pedido inválido: comando, modo, cenário ou controlador desconhecido"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, String>> inesperado(Exception e) {
        log.error("Erro inesperado no painel: {}", e.toString());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("mensagem", "Erro inesperado no painel — veja a janela do painel para detalhes"));
    }
}
