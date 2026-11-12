export function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"})[c]);
}

export function hora(instante) {
    return new Date(instante).toLocaleTimeString("pt-BR", {hour12: false});
}

export function numero(valor, casas = 1) {
    return Number(valor).toLocaleString("pt-BR", {minimumFractionDigits: casas, maximumFractionDigits: casas});
}

export function aviso(mensagem, erro = false) {
    const caixa = document.createElement("div");
    caixa.className = "aviso" + (erro ? " erro" : "");
    caixa.textContent = mensagem;
    document.getElementById("avisos").appendChild(caixa);
    setTimeout(() => caixa.remove(), erro ? 7000 : 4000);
}

export async function postar(url, corpo) {
    let resposta;
    try {
        resposta = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: corpo ? JSON.stringify(corpo) : null
        });
    } catch {
        throw new Error("Painel web inacessível — verifique se o painel está rodando");
    }
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
        throw new Error(dados.mensagem || `Erro ${resposta.status} ao chamar o painel`);
    }
    return dados;
}
