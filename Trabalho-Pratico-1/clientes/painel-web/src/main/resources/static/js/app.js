import {esc} from "./util.js";
import {desenharBarragem} from "./barragem.js";
import {desenharSensores} from "./sensores.js";
import {desenharAtuadores} from "./atuadores.js";
import {desenharControladores} from "./controladores.js";
import {desenharEventos} from "./eventos.js";
import {ligarAcoes} from "./acoes.js";
import {iniciarSom, reagir} from "./som.js";

let sensoresListados = false;

function atualizar(visao) {
    document.body.dataset.nivel = visao.nivel;
    document.getElementById("nome-barragem").textContent = visao.barragem;
    document.getElementById("nivel-rotulo").textContent = visao.nivelRotulo;
    document.getElementById("nivel-detalhe").textContent = visao.nivel === "indisponivel"
        ? "nenhuma réplica respondeu"
        : visao.quorum
            ? `${visao.votosNoNivel} de ${visao.totalReplicas} réplicas concordam${visao.evacuacaoManual ? " · evacuação manual ativa" : ""}`
            : "sem maioria entre as réplicas — exibindo o nível mais grave";
    document.getElementById("lider-atual").textContent = visao.liderId > 0 ? `c${visao.liderId}` : "—";
    document.getElementById("cenario-atual").textContent = `cenário: ${visao.cenario}`;
    document.getElementById("descartadas").textContent = `${visao.descartadas} leituras descartadas`;
    document.getElementById("estado-operacao").textContent =
        `evacuação manual: ${visao.evacuacaoManual ? "SIM" : "não"} · alarme ${visao.alarmeReconhecido ? "reconhecido" : "não reconhecido"}`;
    document.getElementById("motivos").innerHTML = visao.motivos.map(m => `<span>${esc(m)}</span>`).join("");
    document.querySelectorAll("[data-cenario]").forEach(b => b.classList.toggle("ativo", b.dataset.cenario === visao.cenario));

    if (!sensoresListados && visao.sensores.length) {
        document.getElementById("sensor-pico").innerHTML =
            visao.sensores.map(s => `<option value="${esc(s.id)}">${esc(s.id)}</option>`).join("");
        document.getElementById("sensor-pico").value = "PZ-02";
        sensoresListados = true;
    }

    desenharBarragem(visao);
    desenharControladores(visao);
    desenharSensores(visao);
    desenharAtuadores(visao);
    desenharEventos(visao);
    reagir(visao);
}

function conectar() {
    const ponto = document.getElementById("ponto-conexao");
    const texto = document.getElementById("texto-conexao");
    const fonte = new EventSource("/api/fluxo");
    fonte.addEventListener("estado", evento => {
        ponto.classList.add("on");
        texto.textContent = "ao vivo";
        atualizar(JSON.parse(evento.data));
    });
    fonte.onerror = () => {
        ponto.classList.remove("on");
        texto.textContent = "reconectando";
    };
}

setInterval(() => {
    document.getElementById("relogio").textContent = new Date().toLocaleTimeString("pt-BR", {hour12: false});
}, 500);

ligarAcoes();
iniciarSom();
if (new URLSearchParams(location.search).has("estatico")) {
    fetch("/api/estado").then(r => r.json()).then(atualizar);
} else {
    conectar();
}
