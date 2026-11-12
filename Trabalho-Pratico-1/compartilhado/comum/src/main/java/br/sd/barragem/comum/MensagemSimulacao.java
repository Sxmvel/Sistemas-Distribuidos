package br.sd.barragem.comum;

public record MensagemSimulacao(String acao, String alvo) {

    public static final String alterarCenario = "cenario";
    public static final String leituraForjada = "forjada";
    public static final String picoSensor = "pico";
}
