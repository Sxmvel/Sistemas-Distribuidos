import math
import statistics
from collections import Counter


def percentil(valores_ordenados, p):
    if not valores_ordenados:
        return None
    posicao = max(1, math.ceil(p / 100 * len(valores_ordenados)))
    return valores_ordenados[posicao - 1]


def percentil_do_material(valores_ordenados, p):
    if not valores_ordenados:
        return None
    indice = min(len(valores_ordenados) - 1, int((p / 100) * len(valores_ordenados)))
    return valores_ordenados[indice]


def janela(amostras):
    if not amostras:
        return 0.0
    return max(a.fim_s for a in amostras) - min(a.inicio_s for a in amostras)


def resumir(amostras, slo_ms=None, duracao_s=None):
    total = len(amostras)
    sucessos = [a for a in amostras if a.classe == "sucesso"]
    latencias = sorted(a.duracao_ms for a in sucessos)
    erros_aplicacao = [a for a in amostras if a.classe == "erro_aplicacao"]
    erros_transporte = [a for a in amostras if a.classe == "erro_transporte"]
    duracao_s = duracao_s if duracao_s is not None else janela(amostras)

    resumo = {
        "n": total,
        "sucessos": len(sucessos),
        "erros_aplicacao": len(erros_aplicacao),
        "erros_transporte": len(erros_transporte),
        "taxa_de_erro": (total - len(sucessos)) / total if total else 0.0,
        "media_ms": statistics.fmean(latencias) if latencias else None,
        "p50_ms": percentil(latencias, 50),
        "p95_ms": percentil(latencias, 95),
        "p99_ms": percentil(latencias, 99),
        "max_ms": latencias[-1] if latencias else None,
        "duracao_s": duracao_s,
        "vazao_rps": len(sucessos) / duracao_s if duracao_s > 0 else None,
        "erros_por_tipo": dict(Counter(a.detalhe for a in amostras if a.classe != "sucesso")),
    }
    if slo_ms is not None:
        dentro = sum(1 for a in sucessos if a.duracao_ms <= slo_ms)
        resumo["slo_ms"] = slo_ms
        resumo["disponibilidade"] = dentro / total if total else None
    return resumo


def fracao_acima(amostras, limite_ms):
    sucessos = [a for a in amostras if a.classe == "sucesso"]
    if not sucessos:
        return None
    return sum(1 for a in sucessos if a.duracao_ms > limite_ms) / len(sucessos)


def linha_do_tempo(amostras, passo_s=1.0, slo_ms=None):
    if not amostras:
        return []
    fim = max(a.inicio_s for a in amostras)
    baldes = []
    indice = 0
    while indice * passo_s <= fim:
        de, ate = indice * passo_s, (indice + 1) * passo_s
        dentro = [a for a in amostras if de <= a.inicio_s < ate]
        resumo = resumir(dentro, slo_ms=slo_ms, duracao_s=passo_s)
        baldes.append({"de_s": de, "ate_s": ate, **resumo})
        indice += 1
    return baldes
