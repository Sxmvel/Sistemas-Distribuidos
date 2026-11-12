package br.sd.barragem.painel.aplicacao.modelo;

import br.sd.barragem.cliente.ResultadoExecucao;

import java.util.List;

public record ResultadoComandoVisao(boolean sucesso, String requisicaoId, String comando, String mensagem,
                                    boolean repetida, int executadoPor, String preparacao,
                                    List<TentativaVisao> tentativas) {

    public record TentativaVisao(int controlador, boolean sucesso, String detalhe, long duracaoMs) {
    }

    public static ResultadoComandoVisao de(ResultadoExecucao resultado, String preparacao) {
        return new ResultadoComandoVisao(resultado.sucesso(), resultado.requisicaoId(), resultado.tipo().descricao(),
                resultado.resposta().map(r -> r.getMensagem()).orElse("Nenhuma réplica conseguiu executar o comando"),
                resultado.resposta().map(r -> r.getRepetida()).orElse(false),
                resultado.resposta().map(r -> r.getExecutadoPor()).orElse(0),
                preparacao,
                resultado.tentativas().stream()
                        .map(t -> new TentativaVisao(t.controlador(), t.sucesso(), t.detalhe(), t.duracaoMs()))
                        .toList());
    }
}
