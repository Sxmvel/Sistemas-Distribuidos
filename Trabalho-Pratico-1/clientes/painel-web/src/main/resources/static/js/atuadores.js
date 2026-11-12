import {esc} from "./util.js";

const nomes = {
    sirene: ["SR", "Sirene"],
    painelRota: ["PR", "Painel de rota"],
    cancela: ["CN", "Cancela"],
    bomba: ["BR", "Bomba de rebaixamento"]
};

const repouso = ["desligada", "livre", "aberta"];

export function desenharAtuadores(visao) {
    const alvo = document.getElementById("atuadores");
    if (visao.atuadores.length === 0) {
        alvo.innerHTML = `<p class="nota">Sem estado dos atuadores.</p>`;
        return;
    }
    alvo.innerHTML = visao.atuadores.map(atuador => {
        const [sigla, nome] = nomes[atuador.tipo] || ["?", atuador.tipo];
        const classes = ["atuador"];
        if (!repouso.includes(atuador.estado)) {
            classes.push("ativo");
        }
        if (atuador.estado === "tocando") {
            classes.push("tocando");
        }
        return `
            <article class="${classes.join(" ")}">
                <div class="atuador-icone">${sigla}</div>
                <div>
                    <div class="atuador-nome">${esc(atuador.id)} · ${esc(nome)}</div>
                    <div class="atuador-local">${esc(atuador.local)}</div>
                    <div class="atuador-quorum">quórum: ${esc(atuador.apoiadores.join(", ") || "—")}</div>
                </div>
                <div class="atuador-estado">${esc(atuador.estado)}</div>
            </article>`;
    }).join("");
}
