import {numero} from "./util.js";

const posicoes = {
    "PZ-01": [395, 172],
    "PZ-02": [445, 282],
    "PZ-03": [334, 228],
    "IN-01": [525, 210],
    "IN-02": [418, 140],
    "NV-01": [210, 0],
    "PL-01": [130, 72],
    "TB-01": [612, 290]
};

const svg = "http://www.w3.org/2000/svg";
const gotasTotais = 70;
let iniciado = false;

function iniciar() {
    const chuva = document.getElementById("chuva");
    for (let i = 0; i < gotasTotais; i++) {
        const gota = document.createElementNS(svg, "line");
        const x = Math.random() * 900;
        const y = 40 + Math.random() * 230;
        gota.setAttribute("x1", x);
        gota.setAttribute("y1", y);
        gota.setAttribute("x2", x - 4);
        gota.setAttribute("y2", y + 12);
        gota.style.animationDelay = `${(Math.random() * 0.7).toFixed(2)}s`;
        gota.style.display = "none";
        chuva.appendChild(gota);
    }
    const marcadores = document.getElementById("marcadores");
    Object.keys(posicoes).forEach(id => {
        const grupo = document.createElementNS(svg, "g");
        grupo.setAttribute("class", "marcador");
        grupo.setAttribute("id", `marcador-${id}`);
        grupo.innerHTML = `<circle r="7" class="sev-0"></circle><text x="11" y="4"></text><title></title>`;
        marcadores.appendChild(grupo);
    });
    iniciado = true;
}

export function desenharBarragem(visao) {
    if (!iniciado) {
        iniciar();
    }
    const porId = Object.fromEntries(visao.sensores.map(s => [s.id, s]));
    const nivel = porId["NV-01"] ? Math.max(0, Math.min(100, porId["NV-01"].valor)) : 72;
    const altura = nivel / 100 * 172;
    const topo = 300 - altura;
    const reservatorio = document.getElementById("reservatorio");
    reservatorio.setAttribute("y", topo);
    reservatorio.setAttribute("height", altura);
    document.getElementById("linha-agua").setAttribute("d", `M0 ${topo} H420`);

    Object.entries(posicoes).forEach(([id, [x, y]]) => {
        const grupo = document.getElementById(`marcador-${id}`);
        const sensor = porId[id];
        const posY = id === "NV-01" ? topo - 12 : y;
        grupo.setAttribute("transform", `translate(${x},${posY})`);
        grupo.style.display = sensor ? "" : "none";
        if (!sensor) {
            return;
        }
        grupo.querySelector("circle").setAttribute("class", `sev-${sensor.severidade}`);
        grupo.querySelector("text").textContent = `${id} ${numero(sensor.valor, sensor.valor >= 100 ? 0 : 1)}`;
        grupo.querySelector("title").textContent = `${sensor.descricao} — ${numero(sensor.valor)} ${sensor.unidade}`;
    });

    const chuva = porId["PL-01"] ? porId["PL-01"].valor : 0;
    const visiveis = Math.round(Math.min(1, chuva / 90) * gotasTotais);
    document.querySelectorAll("#chuva line").forEach((gota, i) => {
        gota.style.display = i < visiveis ? "" : "none";
    });

    const atuadores = Object.fromEntries(visao.atuadores.map(a => [a.id, a.estado]));
    ["SR-01", "SR-02"].forEach(id => {
        document.getElementById(`svg-${id}`).classList.toggle("tocando", atuadores[id] === "tocando");
    });
    const placa = document.getElementById("svg-PR-01-texto");
    const estadoPlaca = atuadores["PR-01"] || "livre";
    placa.textContent = estadoPlaca.toUpperCase();
    placa.setAttribute("class", `placa-texto ${estadoPlaca}`);
    document.getElementById("braco-cancela").classList.toggle("fechada", atuadores["CN-01"] === "fechada");
    document.querySelector("#svg-BR-01 .bomba").classList.toggle("ligada", atuadores["BR-01"] === "ligada");
}
