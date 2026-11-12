package br.sd.barragem.comum;

public final class TopicosMqtt {

    public static final String raiz = "barragem";
    public static final String todasLeituras = raiz + "/sensores/#";
    public static final String todosComandos = raiz + "/atuadores/+/comando";
    public static final String todosEstadosAtuadores = raiz + "/atuadores/+/estado";
    public static final String simulacao = raiz + "/simulacao/comando";
    public static final String cenarioAtual = raiz + "/simulacao/cenario";

    private TopicosMqtt() {
    }

    public static String leitura(String tipo, String sensorId) {
        return raiz + "/sensores/" + tipo + "/" + sensorId;
    }

    public static String comando(String atuadorId) {
        return raiz + "/atuadores/" + atuadorId + "/comando";
    }

    public static String estadoAtuador(String atuadorId) {
        return raiz + "/atuadores/" + atuadorId + "/estado";
    }
}
