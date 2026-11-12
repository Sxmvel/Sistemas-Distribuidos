import {aviso, postar} from "./util.js";
import {mostrarRastro} from "./eventos.js";
import {somFalha, somSucesso} from "./som.js";

function soar(sucesso) {
    sucesso ? somSucesso() : somFalha();
}

async function executar(botao, acao) {
    botao.disabled = true;
    try {
        return await acao();
    } catch (erro) {
        aviso(erro.message, true);
    } finally {
        botao.disabled = false;
    }
}

function travarComandos(travar) {
    document.querySelectorAll("[data-comando], #evacuar-com-queda").forEach(b => b.disabled = travar);
}

async function enviarComando(tipo) {
    travarComandos(true);
    try {
        const resultado = await postar(`/api/comandos/${tipo}`, {
            operador: document.getElementById("operador").value,
            motivo: document.getElementById("motivo").value
        });
        mostrarRastro(resultado);
        soar(resultado.sucesso);
        aviso(resultado.sucesso ? resultado.mensagem : "Comando falhou", !resultado.sucesso);
    } catch (erro) {
        soar(false);
        aviso(erro.message, true);
    } finally {
        travarComandos(false);
    }
}

export function ligarAcoes() {
    document.querySelectorAll("[data-comando]").forEach(botao =>
        botao.addEventListener("click", () => enviarComando(botao.dataset.comando)));

    document.getElementById("evacuar-com-queda").addEventListener("click", async () => {
        travarComandos(true);
        try {
            const resultado = await postar("/api/demonstracoes/evacuar-com-queda-do-lider");
            mostrarRastro(resultado);
            soar(resultado.sucesso);
            aviso(resultado.sucesso ? "Evacuação confirmada apesar da queda do líder" : "Comando falhou", !resultado.sucesso);
        } catch (erro) {
            soar(false);
            aviso(erro.message, true);
        } finally {
            travarComandos(false);
        }
    });

    document.querySelectorAll("[data-cenario]").forEach(botao =>
        botao.addEventListener("click", () => executar(botao, async () => {
            const resposta = await postar(`/api/laboratorio/cenario/${botao.dataset.cenario}`);
            aviso(resposta.mensagem);
        })));

    document.getElementById("injetar-forjada").addEventListener("click", evento =>
        executar(evento.currentTarget, async () => aviso((await postar("/api/laboratorio/forjada")).mensagem)));

    document.getElementById("injetar-pico").addEventListener("click", evento =>
        executar(evento.currentTarget, async () => {
            const sensor = document.getElementById("sensor-pico").value;
            aviso((await postar(`/api/laboratorio/pico/${sensor}`)).mensagem);
        }));

    document.getElementById("controladores").addEventListener("click", evento => {
        const botao = evento.target.closest("button[data-acao]");
        if (!botao) {
            return;
        }
        const {acao, id, modo} = botao.dataset;
        const url = acao === "modo"
            ? `/api/laboratorio/controladores/${id}/modo/${modo}`
            : `/api/laboratorio/controladores/${id}/${acao}`;
        executar(botao, async () => aviso((await postar(url)).mensagem));
    });
}
