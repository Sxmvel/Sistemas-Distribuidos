package br.sd.barragem.cli.entrada;

import br.sd.barragem.cli.aplicacao.AcompanhamentoTempoReal;
import br.sd.barragem.cli.aplicacao.Formatador;
import br.sd.barragem.cliente.ClienteBarragem;
import br.sd.barragem.cliente.TipoComando;
import io.grpc.Context;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.Scanner;

@Component
public class MenuConsole implements CommandLineRunner {

    private static final String operador = "defesa-civil";

    private final ClienteBarragem cliente;
    private final AcompanhamentoTempoReal acompanhamento;
    private final PrintStream saida = System.out;

    public MenuConsole(ClienteBarragem cliente, AcompanhamentoTempoReal acompanhamento) {
        this.cliente = cliente;
        this.acompanhamento = acompanhamento;
    }

    @Override
    public void run(String... args) {
        Scanner entrada = new Scanner(System.in, StandardCharsets.UTF_8);
        while (true) {
            saida.println("""

                    ===== CLIENTE 2 — DEFESA CIVIL | Barragem Serra Azul (fictícia) =====
                      1) Consultar estado (votação entre as réplicas)
                      2) Acompanhar em tempo real (stream gRPC)
                      3) Acionar evacuação
                      4) Reconhecer alarme
                      5) Encerrar evacuação manual
                      6) Auditoria
                      0) Sair""");
            saida.print("  > ");
            if (!entrada.hasNextLine()) {
                return;
            }
            switch (entrada.nextLine().trim()) {
                case "1" -> saida.println(Formatador.votacao(cliente.consultarComVotacao()));
                case "2" -> acompanhar(entrada);
                case "3" -> comandar(TipoComando.acionarEvacuacao, entrada);
                case "4" -> comandar(TipoComando.reconhecerAlarme, entrada);
                case "5" -> comandar(TipoComando.encerrarEvacuacao, entrada);
                case "6" -> auditoria();
                case "0" -> {
                    return;
                }
                default -> saida.println("  Opção inválida");
            }
        }
    }

    private void acompanhar(Scanner entrada) {
        saida.println("  Acompanhando em tempo real — pressione ENTER para voltar ao menu");
        Context.CancellableContext contexto = acompanhamento.iniciar(saida::println);
        entrada.nextLine();
        contexto.cancel(null);
    }

    private void comandar(TipoComando tipo, Scanner entrada) {
        saida.print("  Motivo (opcional): ");
        String motivo = entrada.hasNextLine() ? entrada.nextLine().trim() : "";
        saida.println("  Enviando '" + tipo.descricao() + "'...");
        saida.println(Formatador.execucao(cliente.executar(tipo, operador, motivo)));
    }

    private void auditoria() {
        cliente.auditoria(25).ifPresentOrElse(lista -> {
            saida.println("\n  Auditoria (fonte: c" + lista.getControladorId() + ", mais recentes primeiro):");
            lista.getEventosList().forEach(e -> saida.println(Formatador.evento(e)));
        }, () -> saida.println("  Nenhuma réplica respondeu"));
    }
}
