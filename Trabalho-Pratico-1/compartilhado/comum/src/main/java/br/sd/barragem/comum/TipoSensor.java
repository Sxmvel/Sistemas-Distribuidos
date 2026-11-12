package br.sd.barragem.comum;

public enum TipoSensor {

    piezometro("kPa", "Pressão neutra no maciço"),
    deslocamento("mm/h", "Velocidade de deslocamento do talude"),
    nivel("%", "Nível do reservatório"),
    chuva("mm/h", "Intensidade de chuva"),
    turbidez("NTU", "Turbidez da drenagem interna");

    private final String unidade;
    private final String descricao;

    TipoSensor(String unidade, String descricao) {
        this.unidade = unidade;
        this.descricao = descricao;
    }

    public String unidade() {
        return unidade;
    }

    public String descricao() {
        return descricao;
    }
}
