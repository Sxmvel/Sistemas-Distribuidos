import {aviso} from "./util.js";

const ordem = {indisponivel: -1, normal: 0, atencao: 1, n1: 2, n2: 3, n3: 4};
const chavePreferencia = "painel-barragem-som";

let contexto = null;
let mestre = null;
let ativo = false;
let sirene = null;
let nivelAnterior = null;
let ultimoBipe = 0;
let eventosVistos = null;

function preparar() {
    if (!contexto) {
        contexto = new AudioContext();
        mestre = contexto.createGain();
        mestre.gain.value = 0.7;
        mestre.connect(contexto.destination);
    }
    if (contexto.state === "suspended") {
        contexto.resume();
    }
}

function tom(frequencia, atraso, duracao, tipo = "sine", volume = 0.18, frequenciaFinal = null) {
    if (!ativo) {
        return;
    }
    const inicio = contexto.currentTime + atraso;
    const oscilador = contexto.createOscillator();
    const ganho = contexto.createGain();
    oscilador.type = tipo;
    oscilador.frequency.setValueAtTime(frequencia, inicio);
    if (frequenciaFinal) {
        oscilador.frequency.exponentialRampToValueAtTime(frequenciaFinal, inicio + duracao);
    }
    ganho.gain.setValueAtTime(0.0001, inicio);
    ganho.gain.exponentialRampToValueAtTime(volume, inicio + 0.015);
    ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
    oscilador.connect(ganho).connect(mestre);
    oscilador.start(inicio);
    oscilador.stop(inicio + duracao + 0.05);
    sinalizar();
}

function ruido(atraso, duracao, volume = 0.12) {
    if (!ativo) {
        return;
    }
    const inicio = contexto.currentTime + atraso;
    const amostras = Math.floor(contexto.sampleRate * duracao);
    const buffer = contexto.createBuffer(1, amostras, contexto.sampleRate);
    const dados = buffer.getChannelData(0);
    for (let i = 0; i < amostras; i++) {
        dados[i] = (Math.random() * 2 - 1) * (Math.random() < 0.3 ? 1 : 0.2);
    }
    const fonte = contexto.createBufferSource();
    const filtro = contexto.createBiquadFilter();
    const ganho = contexto.createGain();
    fonte.buffer = buffer;
    filtro.type = "bandpass";
    filtro.frequency.value = 1400;
    ganho.gain.setValueAtTime(volume, inicio);
    ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
    fonte.connect(filtro).connect(ganho).connect(mestre);
    fonte.start(inicio);
    sinalizar();
}

function ligarSirene() {
    if (sirene || !ativo) {
        return;
    }
    const agora = contexto.currentTime;
    const oscilador = contexto.createOscillator();
    const modulador = contexto.createOscillator();
    const profundidade = contexto.createGain();
    const filtro = contexto.createBiquadFilter();
    const ganho = contexto.createGain();
    oscilador.type = "sawtooth";
    oscilador.frequency.value = 850;
    modulador.frequency.value = 0.45;
    profundidade.gain.value = 360;
    filtro.type = "lowpass";
    filtro.frequency.value = 2200;
    ganho.gain.setValueAtTime(0.0001, agora);
    ganho.gain.exponentialRampToValueAtTime(0.07, agora + 0.6);
    modulador.connect(profundidade).connect(oscilador.frequency);
    oscilador.connect(filtro).connect(ganho).connect(mestre);
    oscilador.start();
    modulador.start();
    sirene = {oscilador, modulador, ganho};
    document.getElementById("botao-som")?.classList.add("sirene");
}

function desligarSirene() {
    if (!sirene) {
        return;
    }
    const agora = contexto.currentTime;
    sirene.ganho.gain.cancelScheduledValues(agora);
    sirene.ganho.gain.setValueAtTime(Math.max(sirene.ganho.gain.value, 0.0001), agora);
    sirene.ganho.gain.exponentialRampToValueAtTime(0.0001, agora + 0.5);
    sirene.oscilador.stop(agora + 0.6);
    sirene.modulador.stop(agora + 0.6);
    sirene = null;
    document.getElementById("botao-som")?.classList.remove("sirene");
}

function subida(nivel) {
    const notas = [523, 659, 784, 1047, 1319].slice(0, Math.max(2, nivel + 1));
    notas.forEach((frequencia, i) => tom(frequencia, i * 0.11, 0.18, "triangle", 0.2));
}

function descida() {
    tom(784, 0, 0.2, "sine", 0.14);
    tom(523, 0.18, 0.3, "sine", 0.14);
}

function bipeDuplo() {
    tom(988, 0, 0.12, "square", 0.08);
    tom(988, 0.2, 0.12, "square", 0.08);
}

function quedaReplica() {
    tom(660, 0, 0.6, "sawtooth", 0.1, 90);
}

function retornoReplica() {
    tom(330, 0, 0.35, "triangle", 0.12, 880);
}

function quarentena() {
    ruido(0, 0.25, 0.16);
    tom(140, 0.02, 0.3, "square", 0.08);
}

function estalo() {
    ruido(0, 0.08, 0.1);
}

export function somSucesso() {
    tom(880, 0, 0.14, "sine", 0.18);
    tom(1320, 0.12, 0.25, "sine", 0.18);
}

export function somFalha() {
    tom(180, 0, 0.35, "square", 0.1);
    tom(150, 0.3, 0.4, "square", 0.1);
}

const somPorEvento = {
    par_caiu: quedaReplica,
    par_voltou: retornoReplica,
    liberacao: retornoReplica,
    quarentena,
    assinatura_invalida: estalo,
    leitura_descartada: estalo
};

function chave(evento) {
    return `${evento.instante}|${evento.tipo}|${evento.origem}|${evento.descricao}`;
}

export function reagir(visao) {
    const nivel = ordem[visao.nivel] ?? 0;
    const tocandoEmCampo = visao.atuadores.some(a => a.tipo === "sirene" && a.estado === "tocando");

    if (nivelAnterior !== null && nivel !== nivelAnterior && nivel >= 0) {
        nivel > nivelAnterior ? subida(nivel) : descida();
    }
    nivelAnterior = nivel;

    if (tocandoEmCampo && !visao.alarmeReconhecido) {
        ligarSirene();
    } else {
        desligarSirene();
    }

    const agora = Date.now();
    if (visao.nivel === "n2" && !visao.alarmeReconhecido && agora - ultimoBipe > 3000) {
        bipeDuplo();
        ultimoBipe = agora;
    }

    const novos = visao.eventos.filter(e => !eventosVistos || !eventosVistos.has(chave(e)));
    if (eventosVistos) {
        const tocados = new Set();
        novos.forEach(e => {
            const som = somPorEvento[e.tipo];
            if (som && !tocados.has(e.tipo) && tocados.size < 2) {
                som();
                tocados.add(e.tipo);
            }
        });
    }
    eventosVistos = new Set(visao.eventos.map(chave));
}

function lerPreferencia() {
    try {
        return localStorage.getItem(chavePreferencia) === "ligado";
    } catch {
        return false;
    }
}

function salvarPreferencia(ligado) {
    try {
        localStorage.setItem(chavePreferencia, ligado ? "ligado" : "desligado");
    } catch {
    }
}

function sinalizar() {
    const botao = document.getElementById("botao-som");
    if (!botao) {
        return;
    }
    botao.classList.remove("soando");
    void botao.offsetWidth;
    botao.classList.add("soando");
}

function verificarBloqueio() {
    setTimeout(() => {
        if (ativo && contexto && contexto.state !== "running") {
            aviso("O navegador bloqueou o áudio. Clique em qualquer lugar da página e tente de novo.", true);
        }
    }, 400);
}

export function iniciarSom() {
    const botao = document.getElementById("botao-som");
    const mostrar = () => {
        botao.textContent = ativo ? "Som ligado" : "Ativar som";
        botao.classList.toggle("ligado", ativo);
        botao.classList.toggle("convite", !ativo);
    };
    const ligar = () => {
        preparar();
        ativo = true;
        salvarPreferencia(true);
        mostrar();
        verificarBloqueio();
    };
    botao.addEventListener("click", () => {
        if (ativo) {
            ativo = false;
            desligarSirene();
            salvarPreferencia(false);
            mostrar();
            aviso("Som desligado");
        } else {
            ligar();
            somSucesso();
            aviso("Som ligado — os alertas do sistema serão tocados");
        }
    });
    if (lerPreferencia()) {
        botao.textContent = "Clique para retomar o som";
        botao.classList.add("convite");
        const retomar = evento => {
            if (evento.target.closest("#botao-som")) {
                return;
            }
            document.removeEventListener("pointerdown", retomar);
            ligar();
        };
        document.addEventListener("pointerdown", retomar);
    } else {
        mostrar();
    }
}
