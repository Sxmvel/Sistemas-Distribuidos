package br.sd.barragem.controlador.dominio;

import java.util.Locale;
import java.util.Optional;

public class VerificadorPlausibilidade {

    private final long janelaTempoMs;

    public VerificadorPlausibilidade(long janelaTempoMs) {
        this.janelaTempoMs = janelaTempoMs;
    }

    public Optional<String> problema(Leitura anterior, Leitura nova, long agora) {
        TabelaLimites.Limites limites = TabelaLimites.de(nova.tipo());
        if (nova.valor() < limites.minimo() || nova.valor() > limites.maximo()) {
            return Optional.of(String.format(Locale.ROOT, "valor %.1f fora da faixa física [%.0f, %.0f]",
                    nova.valor(), limites.minimo(), limites.maximo()));
        }
        if (Math.abs(agora - nova.instante()) > janelaTempoMs) {
            return Optional.of("carimbo de tempo fora da janela aceita (possível replay)");
        }
        if (anterior == null) {
            return Optional.empty();
        }
        if (nova.instante() <= anterior.instante()) {
            return Optional.of("leitura repetida ou fora de ordem (possível replay)");
        }
        double segundos = Math.max(1.0, (nova.instante() - anterior.instante()) / 1000.0);
        double variacao = Math.abs(nova.valor() - anterior.valor());
        if (variacao > limites.variacaoPorSegundo() * segundos) {
            return Optional.of(String.format(Locale.ROOT, "salto de %.1f %s em %.1fs excede o limite físico de %.1f/s",
                    variacao, nova.tipo().unidade(), segundos, limites.variacaoPorSegundo()));
        }
        return Optional.empty();
    }
}
