package br.sd.barragem.controlador.infraestrutura.grpc;

import br.sd.barragem.contrato.EstadoAtuador;
import br.sd.barragem.contrato.EstadoPar;
import br.sd.barragem.contrato.EstadoSistema;
import br.sd.barragem.contrato.LeituraSensor;
import br.sd.barragem.contrato.Nivel;
import br.sd.barragem.contrato.PedidoComando;
import br.sd.barragem.contrato.RespostaComando;
import br.sd.barragem.controlador.aplicacao.modelo.PedidoOperador;
import br.sd.barragem.controlador.aplicacao.modelo.ResultadoComando;
import br.sd.barragem.controlador.aplicacao.modelo.RetratoEstado;
import br.sd.barragem.controlador.dominio.NivelEmergencia;
import br.sd.barragem.controlador.dominio.Operacao;
import br.sd.barragem.controlador.dominio.RegistroAuditoria;
import br.sd.barragem.controlador.dominio.TabelaLimites;
import br.sd.barragem.controlador.dominio.TipoOperacao;

import java.util.List;

public final class ConversorProto {

    private ConversorProto() {
    }

    public static Nivel nivel(NivelEmergencia nivel) {
        return Nivel.forNumber(nivel.ordinal());
    }

    public static NivelEmergencia nivel(Nivel nivel) {
        return NivelEmergencia.values()[nivel.getNumber()];
    }

    public static br.sd.barragem.contrato.Operacao operacao(Operacao operacao) {
        return br.sd.barragem.contrato.Operacao.newBuilder()
                .setSeq(operacao.seq())
                .setRequisicaoId(operacao.requisicaoId())
                .setTipo(operacao.tipo().name())
                .setOperador(texto(operacao.operador()))
                .setMotivo(texto(operacao.motivo()))
                .setInstante(operacao.instante())
                .setLiderId(operacao.liderId())
                .build();
    }

    public static Operacao operacao(br.sd.barragem.contrato.Operacao operacao) {
        return new Operacao(operacao.getSeq(), operacao.getRequisicaoId(), TipoOperacao.valueOf(operacao.getTipo()),
                operacao.getOperador(), operacao.getMotivo(), operacao.getInstante(), operacao.getLiderId());
    }

    public static PedidoOperador pedido(PedidoComando pedido) {
        return new PedidoOperador(pedido.getRequisicaoId(), pedido.getOperador(), pedido.getMotivo());
    }

    public static PedidoComando pedido(PedidoOperador pedido) {
        return PedidoComando.newBuilder()
                .setRequisicaoId(pedido.requisicaoId())
                .setOperador(texto(pedido.operador()))
                .setMotivo(texto(pedido.motivo()))
                .build();
    }

    public static RespostaComando resposta(ResultadoComando resultado) {
        return RespostaComando.newBuilder()
                .setSucesso(resultado.sucesso())
                .setMensagem(resultado.mensagem())
                .setSeq(resultado.seq())
                .setExecutadoPor(resultado.executadoPor())
                .setRepetida(resultado.repetida())
                .build();
    }

    public static ResultadoComando resposta(RespostaComando resposta) {
        return new ResultadoComando(resposta.getSucesso(), resposta.getMensagem(), resposta.getSeq(),
                resposta.getExecutadoPor(), resposta.getRepetida());
    }

    public static br.sd.barragem.contrato.EventoAuditoria evento(RegistroAuditoria registro) {
        return br.sd.barragem.contrato.EventoAuditoria.newBuilder()
                .setSeq(registro.seq())
                .setInstante(registro.instante())
                .setTipo(registro.tipo())
                .setDescricao(texto(registro.descricao()))
                .setOrigem(texto(registro.origem()))
                .build();
    }

    public static EstadoSistema estado(RetratoEstado retrato) {
        EstadoSistema.Builder construtor = EstadoSistema.newBuilder()
                .setControladorId(retrato.controladorId())
                .setLiderId(retrato.liderId())
                .setNivel(nivel(retrato.nivel()))
                .setNivelAutomatico(nivel(retrato.nivelAutomatico()))
                .setEvacuacaoManual(retrato.evacuacaoManual())
                .setAlarmeReconhecido(retrato.alarmeReconhecido())
                .setUltimoSeq(retrato.ultimoSeq())
                .setLeiturasDescartadas(retrato.descartadas())
                .addAllMotivos(retrato.motivos())
                .setInstante(retrato.instante());
        retrato.sensores().forEach(s -> {
            TabelaLimites.Limites limites = TabelaLimites.de(s.tipo());
            construtor.addSensores(LeituraSensor.newBuilder()
                    .setSensorId(s.id())
                    .setTipo(s.tipo().name())
                    .setValor(s.valor())
                    .setUnidade(s.tipo().unidade())
                    .setSeveridade(s.severidade())
                    .setInstante(s.instante())
                    .addAllLimiares(List.of(limites.atencao(), limites.n1(), limites.n2(), limites.n3())));
        });
        retrato.atuadores().forEach(a -> construtor.addAtuadores(EstadoAtuador.newBuilder()
                .setAtuadorId(a.id())
                .setTipo(a.tipo())
                .setEstado(a.estado())
                .addAllApoiadores(a.apoiadores().stream().map(c -> "c" + c).toList())
                .setInstante(a.instante())));
        retrato.pares().forEach(p -> construtor.addPares(EstadoPar.newBuilder()
                .setId(p.id())
                .setVivo(p.vivo())
                .setQuarentena(p.quarentena())
                .setNivel(nivel(p.nivel()))
                .setUltimoSeq(p.ultimoSeq())));
        return construtor.build();
    }

    private static String texto(String valor) {
        return valor == null ? "" : valor;
    }
}
