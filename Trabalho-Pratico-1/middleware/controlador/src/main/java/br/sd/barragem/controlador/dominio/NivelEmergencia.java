package br.sd.barragem.controlador.dominio;

public enum NivelEmergencia {

    normal("NORMAL"),
    atencao("ATENÇÃO"),
    n1("EMERGÊNCIA N1"),
    n2("EMERGÊNCIA N2"),
    n3("EMERGÊNCIA N3");

    private final String rotulo;

    NivelEmergencia(String rotulo) {
        this.rotulo = rotulo;
    }

    public String rotulo() {
        return rotulo;
    }

    public boolean acimaDe(NivelEmergencia outro) {
        return ordinal() > outro.ordinal();
    }
}
