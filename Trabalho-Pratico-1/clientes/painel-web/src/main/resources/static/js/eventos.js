import {esc, hora} from "./util.js";

const rotulos = {
    operacao: "operação replicada",
    nivel: "mudança de nível",
    quarentena: "quarentena",
    liberacao: "fim da quarentena",
    par_caiu: "réplica caiu",
    par_voltou: "réplica voltou",
    lideranca: "liderança",
    sincronizacao: "sincronização",
    leitura_descartada: "leitura descartada",
    assinatura_invalida: "assinatura inválida",
    sensor_recalibrado: "sensor recalibrado"
};

export function desenharEventos(visao) {
    const lider = visao.controladores.find(c => c.lider);
    document.getElementById("fonte-eventos").textContent = lider ? `auditoria de c${lider.id}` : "auditoria";
    document.getElementById("eventos").innerHTML = visao.eventos.map(e => {
        const resumo = e.descricao.split(" | ")[0];
        return `
        <li class="evento ${esc(e.tipo)}" title="${esc(e.descricao)}">
            <span class="evento-hora">${hora(e.instante)}</span>
            <div>
                <div class="evento-tipo">${esc(rotulos[e.tipo] || e.tipo)}${e.seq > 0 ? ` · seq ${e.seq}` : ""} · ${esc(e.origem)}</div>
                <div>${esc(resumo)}</div>
            </div>
        </li>`;
    }).join("");
}

export function mostrarRastro(resultado) {
    const tentativas = resultado.tentativas.map(t => `
        <li><span class="${t.sucesso ? "ok" : "falha"}">${t.sucesso ? "OK" : "FALHOU"}</span>
            c${t.controlador} (${t.duracaoMs} ms) — ${esc(t.detalhe)}</li>`).join("");
    document.getElementById("rastro").innerHTML = `
        <div class="rastro-titulo">Rastro da última requisição · ${esc(resultado.comando)}</div>
        ${resultado.preparacao ? `<div class="rastro-preparo">Preparação: ${esc(resultado.preparacao)}</div>` : ""}
        <div class="rastro-id">requisicao_id = ${esc(resultado.requisicaoId)}</div>
        <ol>${tentativas}</ol>
        <div class="rastro-resultado">
            <span class="${resultado.sucesso ? "ok" : "falha"}">${resultado.sucesso ? "SUCESSO" : "FALHA"}</span>
            — ${esc(resultado.mensagem)}${resultado.repetida ? " <strong>(deduplicada pelo id: não executou duas vezes)</strong>" : ""}
        </div>`;
}
