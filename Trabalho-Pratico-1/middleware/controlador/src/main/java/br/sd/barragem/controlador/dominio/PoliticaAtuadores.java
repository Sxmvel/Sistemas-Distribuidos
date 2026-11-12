package br.sd.barragem.controlador.dominio;

import br.sd.barragem.comum.Dispositivos;

import java.util.LinkedHashMap;
import java.util.Map;

public class PoliticaAtuadores {

    public Map<String, String> estadosDesejados(NivelEmergencia nivel) {
        Map<String, String> desejados = new LinkedHashMap<>();
        for (Dispositivos.Atuador atuador : Dispositivos.atuadores) {
            desejados.put(atuador.id(), switch (atuador.tipo()) {
                case sirene -> nivel == NivelEmergencia.n3 ? "tocando" : "desligada";
                case painelRota -> switch (nivel) {
                    case normal -> "livre";
                    case atencao, n1 -> "atencao";
                    case n2 -> "preparar";
                    case n3 -> "evacuar";
                };
                case cancela -> nivel.acimaDe(NivelEmergencia.n1) ? "fechada" : "aberta";
                case bomba -> nivel.acimaDe(NivelEmergencia.normal) ? "ligada" : "desligada";
            });
        }
        return desejados;
    }
}
