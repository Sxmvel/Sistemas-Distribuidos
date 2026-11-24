import statistics, sys, time, requests

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/dispositivos"

amostras = []
erros = 0
for _ in range(100):
    inicio = time.perf_counter()
    try:
        r = requests.get(url, timeout=1)
        r.raise_for_status()
        amostras.append((time.perf_counter()-inicio)*1000)
    except requests.RequestException:
        erros += 1

amostras.sort()
def perc(p):
    if not amostras: return None
    idx = min(len(amostras)-1, int((p/100)*len(amostras)))
    return amostras[idx]

print("n", len(amostras), "erros", erros)
print("media", statistics.mean(amostras))
print("p50", perc(50), "p95", perc(95), "p99", perc(99))
