package br.sd.barragem.cliente;

import br.sd.barragem.contrato.RespostaComando;

import java.util.List;
import java.util.Optional;

public record ResultadoExecucao(String requisicaoId, TipoComando tipo, Optional<RespostaComando> resposta,
                                List<Tentativa> tentativas) {

    public record Tentativa(int controlador, boolean sucesso, String detalhe, long duracaoMs) {
    }

    public boolean sucesso() {
        return resposta.map(RespostaComando::getSucesso).orElse(false);
    }
}
