package br.sd.barragem.controlador.aplicacao.porta;

import br.sd.barragem.controlador.dominio.RegistroAuditoria;

import java.util.List;

public interface RepositorioAuditoria {

    void registrar(RegistroAuditoria registro);

    List<RegistroAuditoria> recentes(int limite);
}
