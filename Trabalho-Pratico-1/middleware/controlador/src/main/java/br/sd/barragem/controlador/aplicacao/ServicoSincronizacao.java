package br.sd.barragem.controlador.aplicacao;

import br.sd.barragem.controlador.aplicacao.porta.ComunicacaoPares;
import br.sd.barragem.controlador.dominio.Operacao;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ServicoSincronizacao {

    private final ComunicacaoPares pares;
    private final RegistroOperacoes registro;
    private final Auditoria auditoria;

    public ServicoSincronizacao(ComunicacaoPares pares, RegistroOperacoes registro, Auditoria auditoria) {
        this.pares = pares;
        this.registro = registro;
        this.auditoria = auditoria;
    }

    public void alcancar(int parId) {
        long antes = registro.ultimoSeq();
        List<Operacao> faltantes = pares.sincronizar(parId, antes);
        int aplicadas = 0;
        for (Operacao operacao : faltantes) {
            try {
                if (registro.aplicar(operacao)) {
                    aplicadas++;
                }
            } catch (LacunaException e) {
                break;
            }
        }
        if (aplicadas > 0) {
            auditoria.registrar("sincronizacao", "Recebidas " + aplicadas + " operações de c" + parId
                    + " (seq " + (antes + 1) + " a " + registro.ultimoSeq() + ")");
        }
    }
}
