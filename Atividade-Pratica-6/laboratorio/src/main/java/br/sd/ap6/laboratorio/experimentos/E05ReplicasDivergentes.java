package br.sd.ap6.laboratorio.experimentos;

import br.sd.ap6.integridade.adulteracao.Atacante;
import br.sd.ap6.integridade.validacao.Validador;
import br.sd.ap6.laboratorio.relatorio.Caixa;
import br.sd.ap6.laboratorio.relatorio.Diagrama;
import br.sd.ap6.laboratorio.relatorio.Formato;
import br.sd.ap6.laboratorio.relatorio.Ramo;
import br.sd.ap6.laboratorio.relatorio.ResultadoExperimento;
import br.sd.ap6.laboratorio.relatorio.Tabela;
import br.sd.ap6.nucleo.dominio.Bloco;
import br.sd.ap6.nucleo.dominio.Cadeia;
import br.sd.ap6.replicacao.reconciliacao.CadeiaMaisLongaVence;
import br.sd.ap6.replicacao.reconciliacao.Reconciliador;
import br.sd.ap6.replicacao.reconciliacao.RegraDeReconciliacao;
import br.sd.ap6.replicacao.reconciliacao.ResultadoReconciliacao;
import br.sd.ap6.replicacao.rede.Recepcao;
import br.sd.ap6.replicacao.rede.Replica;
import br.sd.ap6.replicacao.rede.TipoDivergencia;
import java.util.ArrayList;
import java.util.List;

public final class E05ReplicasDivergentes implements Experimento {

    private static final int tamanhoDoPrefixo = 15;
    private static final int blocoFraudado = 5;
    private static final int blocosVisiveisDoTronco = 1;

    private final Validador validador = new Validador();
    private final Atacante atacante = new Atacante();
    private final RegraDeReconciliacao regra = new CadeiaMaisLongaVence();
    private final Reconciliador reconciliador = new Reconciliador(regra);

    @Override
    public String id() {
        return "E05";
    }

    @Override
    public String titulo() {
        return "Réplicas divergentes e regra de reconciliação";
    }

    @Override
    public ResultadoExperimento executar() {
        var referencia = CadeiaDeReferencia.gerar();
        var prefixo = referencia.prefixo(tamanhoDoPrefixo);
        var resultado = ResultadoExperimento.de(id(), titulo())
                .objetivo("Simular cópias da cadeia que recebem blocos diferentes, detectar a divergência e "
                        + "aplicar uma regra de reconciliação, observando o que ela resolve e o que ela não resolve.")
                .manipulacao("Réplicas partindo de um prefixo comum de " + tamanhoDoPrefixo + " blocos (0 a "
                        + (tamanhoDoPrefixo - 1) + "), em quatro cenários: omissão de mensagem, partição, empate "
                        + "e réplica bizantina. Regra: " + regra.nome() + ".")
                .esperado("Cada cópia continua válida localmente; a regra faz as réplicas convergirem, mas "
                        + "descarta blocos do ramo perdedor e aceita uma fraude reescrita que seja mais longa.");

        var resumo = new Tabela("Resumo dos cenários", "Cenário", "Modelo de falha", "Divergência",
                "Ancestral comum", "Decisão", "Vencedora", "Blocos descartados", "Transações órfãs", "Convergiram");
        resultado.tabela(resumo);

        cenarioOmissao(resultado, resumo, prefixo);
        var particao = cenarioParticao(resultado, resumo, prefixo);
        cenarioEmpate(resultado, resumo, prefixo);
        cenarioBizantino(resultado, resumo, referencia);

        return resultado
                .obtido("as réplicas convergiram nos 5 casos; a partição descartou "
                        + particao.descartados().size() + " blocos de " + particao.perdedora()
                        + " e a réplica bizantina venceu ao apresentar uma fraude reescrita mais longa.")
                .diagrama(diagrama(particao, prefixo))
                .observacao("Omissão: a validação local percebe a lacuna (o bloco seguinte chega fora de ordem), "
                        + "mas não há conflito. Basta sincronizar: uma cópia é prefixo da outra.")
                .observacao("Partição: os dois ramos são válidos e a validação local não tem como escolher entre "
                        + "eles. A regra converge as réplicas, mas o ramo perdedor é descartado e suas transações "
                        + "voltam a ficar pendentes. O que parecia confirmado em sul deixou de estar, por isso "
                        + "\"incluído em um bloco\" não significa \"irreversível\".")
                .observacao("Empate: o menor hash da ponta é um critério arbitrário, mas determinístico. Cada réplica "
                        + "aplica a regra sozinha e chega à mesma escolha, sem precisar combinar.")
                .observacao("D1 aparece como \"atraso\", e não como fork: o detector compara os hashes armazenados, "
                        + "e a adulteração sem reescrita não muda nenhum deles. Comparar hashes não basta; é a "
                        + "validação (recalcular cada hash) que revela a fraude, por isso o reconciliador valida "
                        + "as duas cópias antes de aplicar a regra.")
                .observacao("Bizantino: a validação barra a adulteração ingênua, mas a fraude reescrita com um bloco "
                        + "a mais vence. Uma regra sem custo pode ser fraudada por quem gera blocos de graça. "
                        + "Protocolos reais exigem trabalho acumulado (PoW) ou stake (PoS), assinaturas e maioria honesta.")
                .construir();
    }

    private void cenarioOmissao(ResultadoExperimento.Construtor resultado, Tabela resumo, Cadeia prefixo) {
        var norte = new Replica("norte", prefixo);
        var sul = new Replica("sul", prefixo);
        var produzidos = CadeiaDeReferencia.geradorDerivado(1).gerar(3).stream().map(norte::produzir).toList();

        resultado.log("cenário A — omissão: norte produz 3 blocos e a mensagem do bloco "
                + produzidos.get(1).indice() + " se perde");
        var entregas = new Tabela("Cenário A — entregas de norte para sul", "Bloco", "Mensagem", "Resultado em sul");
        Recepcao ultima = null;
        for (int i = 0; i < produzidos.size(); i++) {
            var bloco = produzidos.get(i);
            if (i == 1) {
                entregas.linha(bloco.indice(), "perdida (omissão)", "—");
                resultado.log("  bloco " + bloco.indice() + ": mensagem perdida");
                continue;
            }
            ultima = sul.receber(bloco);
            entregas.linha(bloco.indice(), "entregue", ultima.aceito() ? "aceito" : "recusado: " + ultima.motivo());
            resultado.log("  bloco " + bloco.indice() + ": " + (ultima.aceito() ? "aceito" : "recusado — " + ultima.motivo()));
        }
        resultado.tabela(entregas);
        resultado.verificar("A: sul recusa o bloco que chega depois da lacuna", ultima != null && !ultima.aceito());

        var r = reconciliar(resultado, resumo, "A", "omissão de mensagem", norte, sul);
        resultado.verificar("A: divergência classificada como atraso, não fork",
                r.divergencia().tipo() == TipoDivergencia.atraso);
        resultado.verificar("A: nenhum bloco descartado", r.descartados().isEmpty());
    }

    private ResultadoReconciliacao cenarioParticao(ResultadoExperimento.Construtor resultado, Tabela resumo,
                                                   Cadeia prefixo) {
        var norte = new Replica("norte", prefixo);
        var sul = new Replica("sul", prefixo);
        CadeiaDeReferencia.geradorDerivado(2).gerar(6).forEach(norte::produzir);
        CadeiaDeReferencia.geradorDerivado(3).gerar(4).forEach(sul::produzir);

        resultado.log("");
        resultado.log("cenário B — partição: norte produz 6 blocos e sul produz 4, sem comunicação");
        resultado.log("  norte: " + norte.cadeia().tamanho() + " blocos, " + validador.validar(norte.cadeia()).mensagem()
                + ", ponta=" + norte.cadeia().ponta().hash());
        resultado.log("  sul:   " + sul.cadeia().tamanho() + " blocos, " + validador.validar(sul.cadeia()).mensagem()
                + ", ponta=" + sul.cadeia().ponta().hash());
        resultado.verificar("B: a cópia de norte é válida localmente", validador.validar(norte.cadeia()).valida());
        resultado.verificar("B: a cópia de sul é válida localmente", validador.validar(sul.cadeia()).valida());

        var recepcao = sul.receber(norte.cadeia().bloco(tamanhoDoPrefixo));
        resultado.log("  rede volta: sul recebe o bloco " + tamanhoDoPrefixo + " de norte -> "
                + (recepcao.aceito() ? "aceito" : "recusado — " + recepcao.motivo()));
        resultado.verificar("B: sul não consegue simplesmente anexar o ramo de norte", !recepcao.aceito());

        resultado.tabela(disputa(norte.cadeia(), sul.cadeia()));
        logRamos(resultado, norte.cadeia(), sul.cadeia());

        var r = reconciliar(resultado, resumo, "B", "partição de rede", norte, sul);
        resultado.verificar("B: divergência classificada como fork", r.divergencia().tipo() == TipoDivergencia.fork);
        resultado.verificar("B: ancestral comum é o bloco " + (tamanhoDoPrefixo - 1),
                r.divergencia().ancestralComum() == tamanhoDoPrefixo - 1);
        resultado.verificar("B: norte (mais longa) vence", r.vencedora().equals("norte"));
        resultado.verificar("B: os 4 blocos de sul são descartados e as 4 transações ficam órfãs",
                r.descartados().size() == 4 && r.transacoesOrfas().size() == 4);
        return r;
    }

    private void cenarioEmpate(ResultadoExperimento.Construtor resultado, Tabela resumo, Cadeia prefixo) {
        var leste = new Replica("leste", prefixo);
        var oeste = new Replica("oeste", prefixo);
        CadeiaDeReferencia.geradorDerivado(4).gerar(3).forEach(leste::produzir);
        CadeiaDeReferencia.geradorDerivado(5).gerar(3).forEach(oeste::produzir);

        var vistaDeLeste = regra.escolher(leste.cadeia(), oeste.cadeia()).vencedora();
        var vistaDeOeste = regra.escolher(oeste.cadeia(), leste.cadeia()).vencedora();
        resultado.log("");
        resultado.log("cenário C — empate: leste e oeste produzem 3 blocos cada");
        resultado.log("  ponta de leste = " + leste.cadeia().ponta().hash());
        resultado.log("  ponta de oeste = " + oeste.cadeia().ponta().hash());
        resultado.verificar("C: leste e oeste chegam à mesma escolha aplicando a regra cada uma do seu lado",
                vistaDeLeste.equals(vistaDeOeste));

        var r = reconciliar(resultado, resumo, "C", "partição com empate", leste, oeste);
        resultado.verificar("C: empate resolvido pelo menor hash da ponta", r.motivo().startsWith("empate"));
    }

    private void cenarioBizantino(ResultadoExperimento.Construtor resultado, Tabela resumo, Cadeia referencia) {
        var original = referencia.bloco(blocoFraudado).dados();
        var fraude = original.substring(0, original.indexOf("->")) + "->M:1000";
        var blocoExtra = CadeiaDeReferencia.geradorDerivado(6).proxima();
        resultado.log("");
        resultado.log("cenário D — bizantino: mallory troca \"" + original + "\" por \"" + fraude
                + "\" no bloco " + blocoFraudado + " e acrescenta 1 bloco para ficar mais longa");

        var honesta = new Replica("honesta", referencia);
        var ingenua = new Replica("mallory", atacante.alterarDados(referencia, blocoFraudado, fraude));
        ingenua.produzir(blocoExtra);
        var r1 = reconciliar(resultado, resumo, "D1", "bizantino sem reescrita", honesta, ingenua);
        resultado.verificar("D1: a cópia adulterada é rejeitada mesmo sendo mais longa",
                r1.vencedora().equals("honesta"));

        var honesta2 = new Replica("honesta", referencia);
        var reescrita = new Replica("mallory", atacante.fraudar(referencia, blocoFraudado, fraude));
        reescrita.produzir(blocoExtra);
        var r2 = reconciliar(resultado, resumo, "D2", "bizantino com reescrita", honesta2, reescrita);
        resultado.verificar("D2: a fraude reescrita e mais longa vence", r2.vencedora().equals("mallory"));
        resultado.verificar("D2: a réplica honesta passa a guardar a transação fraudada",
                honesta2.cadeia().bloco(blocoFraudado).dados().equals(fraude));
        resultado.verificar("D2: a transação honesta original fica órfã", r2.transacoesOrfas().equals(List.of(original)));
    }

    private ResultadoReconciliacao reconciliar(ResultadoExperimento.Construtor resultado, Tabela resumo,
                                               String cenario, String modelo, Replica a, Replica b) {
        var r = reconciliador.reconciliar(a, b);
        var convergiram = a.cadeia().equals(b.cadeia()) && validador.validar(a.cadeia()).valida();
        resumo.linha(cenario, modelo, r.divergencia().tipo().descricao(), r.divergencia().ancestralComum(),
                r.motivo(), r.vencedora(), r.descartados().size(), r.transacoesOrfas().size(),
                Formato.simOuNao(convergiram));
        resultado.log("  " + cenario + ": " + r.divergencia().tipo().descricao() + ", ancestral comum="
                + r.divergencia().ancestralComum() + " -> vence " + r.vencedora() + ": " + r.motivo());
        r.descartados().forEach(bloco -> resultado.log("    descartado " + CadeiaDeReferencia.linhaDeLog(bloco)));
        if (!r.transacoesOrfas().isEmpty()) {
            resultado.log("    transações que voltam à fila: " + r.transacoesOrfas());
        }
        resultado.log("    ponta final das duas réplicas = " + r.pontaFinal());
        resultado.verificar(cenario + ": as duas réplicas terminam com a mesma cadeia válida", convergiram);
        return r;
    }

    private Tabela disputa(Cadeia norte, Cadeia sul) {
        var tabela = new Tabela("Cenário B — blocos em disputa depois do bloco " + (tamanhoDoPrefixo - 1),
                "Bloco", "Dados em norte", "Hash em norte", "Dados em sul", "Hash em sul");
        for (int i = tamanhoDoPrefixo; i < Math.max(norte.tamanho(), sul.tamanho()); i++) {
            tabela.linha(i,
                    i < norte.tamanho() ? norte.bloco(i).dados() : "—",
                    i < norte.tamanho() ? Formato.curto(norte.bloco(i).hash()) : "—",
                    i < sul.tamanho() ? sul.bloco(i).dados() : "—",
                    i < sul.tamanho() ? Formato.curto(sul.bloco(i).hash()) : "—");
        }
        return tabela;
    }

    private void logRamos(ResultadoExperimento.Construtor resultado, Cadeia norte, Cadeia sul) {
        norte.desde(tamanhoDoPrefixo).forEach(b -> resultado.log("  norte " + CadeiaDeReferencia.linhaDeLog(b)));
        sul.desde(tamanhoDoPrefixo).forEach(b -> resultado.log("  sul   " + CadeiaDeReferencia.linhaDeLog(b)));
    }

    private Diagrama diagrama(ResultadoReconciliacao r, Cadeia prefixo) {
        var ancestral = r.divergencia().ancestralComum();
        var primeiroVisivel = ancestral - blocosVisiveisDoTronco + 1;
        var tronco = new ArrayList<Caixa>();
        tronco.add(new Caixa("#0 … #" + (primeiroVisivel - 1), primeiroVisivel + " blocos", "em comum"));
        prefixo.blocos().subList(primeiroVisivel, ancestral + 1).forEach(b -> tronco.add(caixa(b)));

        var venceuA = r.vencedora().equals("norte");
        var superior = new Ramo("norte", venceuA ? "mantido pela regra" : "descartado",
                r.divergencia().ramoA().stream().map(this::caixa).toList(), venceuA);
        var inferior = new Ramo("sul", venceuA
                ? "descartado: " + r.transacoesOrfas().size() + " transações voltam à fila"
                : "mantido pela regra",
                r.divergencia().ramoB().stream().map(this::caixa).toList(), !venceuA);
        return new Diagrama("diagrama-replicas.png",
                "Duas réplicas divergentes depois de uma partição (E05, cenário B)",
                tronco, superior, inferior,
                List.of("As setas apontam para o bloco anterior (hash_anterior). Os dois ramos partem do bloco "
                                + ancestral + " e passam na validação local de cada réplica.",
                        "Regra: " + regra.nome() + ". Resultado: vence " + r.vencedora() + ", " + r.motivo()
                                + "; os blocos de " + r.perdedora() + " são descartados."));
    }

    private Caixa caixa(Bloco bloco) {
        return new Caixa("#" + bloco.indice(), bloco.dados(), bloco.hash().substring(0, 10));
    }
}
