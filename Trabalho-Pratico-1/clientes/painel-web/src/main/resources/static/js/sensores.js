import {esc, numero} from "./util.js";

export function desenharSensores(visao) {
    const alvo = document.getElementById("sensores");
    if (visao.sensores.length === 0) {
        alvo.innerHTML = `<p class="nota">Sem dados: nenhuma réplica confiável respondeu.</p>`;
        return;
    }
    alvo.innerHTML = visao.sensores.map(sensor => {
        const limiares = sensor.limiares || [];
        const maximo = limiares.length ? limiares[limiares.length - 1] * 1.25 : Math.max(sensor.valor, 1);
        const largura = Math.min(100, Math.max(0, sensor.valor / maximo * 100));
        const marcas = limiares.map(l => `<span class="marca-limiar" style="left:${(l / maximo * 100).toFixed(1)}%"></span>`).join("");
        return `
            <article class="sensor" data-sev="${sensor.severidade}">
                <div class="sensor-topo"><span>${esc(sensor.id)}</span><span>${"●".repeat(sensor.severidade) || "○"}</span></div>
                <div class="sensor-desc">${esc(sensor.descricao)}<br>${esc(sensor.local)}</div>
                <div class="sensor-valor">${numero(sensor.valor)}<small>${esc(sensor.unidade)}</small></div>
                <div class="barra"><div class="barra-preenchida" style="width:${largura.toFixed(1)}%"></div>${marcas}</div>
            </article>`;
    }).join("");
}
