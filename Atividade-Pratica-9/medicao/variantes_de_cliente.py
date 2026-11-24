import json
import statistics
import sys
import time

import requests


def mediana_ms(chamada, repeticoes):
    valores = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        chamada()
        valores.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(valores)


def principal():
    url = sys.argv[1]
    repeticoes = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    sessao = requests.Session()
    sessao.get(url, timeout=1)
    resultado = {
        "requests.get(url, timeout=1)": mediana_ms(lambda: requests.get(url, timeout=1), repeticoes),
        "requests.get(url)": mediana_ms(lambda: requests.get(url), repeticoes),
        "Session().get(url, timeout=1)": mediana_ms(lambda: sessao.get(url, timeout=1), repeticoes),
    }
    print(json.dumps(resultado))


if __name__ == "__main__":
    principal()
