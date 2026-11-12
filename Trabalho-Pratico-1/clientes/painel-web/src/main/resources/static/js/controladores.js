import {esc} from "./util.js";

export function desenharControladores(visao) {
    const consenso = document.getElementById("consenso");
    const responderam = visao.controladores.filter(c => c.respondeu).length;
    consenso.textContent = visao.quorum
        ? `consenso ${visao.votosNoNivel}/${visao.totalReplicas} → ${visao.nivelRotulo}`
        : `sem maioria (${responderam}/${visao.totalReplicas} responderam)`;

    document.getElementById("controladores").innerHTML = visao.controladores.map(c => {
        const divergente = c.respondeu && c.divergencias.length > 0;
        const classes = ["controlador", !c.respondeu ? "fora" : divergente ? "divergente" : ""].join(" ");
        const selos = [
            c.lider ? `<span class="selo lider">LÍDER</span>` : "",
            c.quarentenadoPor.length ? `<span class="selo quarentena">QUARENTENA (por ${c.quarentenadoPor.map(i => "c" + i).join(", ")})</span>` : "",
            c.modo !== "honesto" ? `<span class="selo modo-${esc(c.modo)}">modo ${esc(c.modo)}</span>` : ""
        ].join("");
        const voto = !c.respondeu
            ? `<span class="ruim">SEM RESPOSTA</span><span>${esc(c.erro.split(":")[0])}</span>`
            : `<span>informa <strong>${esc(c.nivelRotulo)}</strong></span><span class="${divergente ? "ruim" : "ok"}">${divergente ? "DIVERGENTE" : "concorda"}</span>`;
        const lista = divergente
            ? `<ul class="divergencias">${c.divergencias.map(d => `<li>${esc(d)}</li>`).join("")}</ul>`
            : "";
        const acoes = c.respondeu
            ? `<button class="botao mini" data-acao="desligar" data-id="${c.id}">Derrubar</button>
               <button class="botao mini" data-acao="modo" data-modo="malicioso" data-id="${c.id}">Malicioso</button>
               <button class="botao mini" data-acao="modo" data-modo="intermitente" data-id="${c.id}">Intermitente</button>
               <button class="botao mini" data-acao="modo" data-modo="honesto" data-id="${c.id}">Honesto</button>`
            : `<button class="botao mini" data-acao="religar" data-id="${c.id}">Religar c${c.id}</button>`;
        return `
            <article class="${classes}">
                <div class="controlador-topo"><span class="controlador-nome">c${c.id}</span>${selos}
                    <span class="selo" style="margin-left:auto">seq ${c.ultimoSeq}</span></div>
                <div class="controlador-voto">${voto}</div>
                ${lista}
                <div class="controlador-acoes">${acoes}</div>
            </article>`;
    }).join("");
}
