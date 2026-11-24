import sys
import time

from laboratorio import (
    e01_referencia,
    e02_media_e_percentis,
    e03_amplificacao_da_cauda,
    e04_carga_e_saturacao,
    e05_correlacao_e_trace,
    e06_caos_queda_de_replica,
    e07_caos_classes_de_erro,
)
from laboratorio.comum import pasta_de_evidencias
from laboratorio.relatorio import gerar

experimentos = (
    e01_referencia,
    e02_media_e_percentis,
    e03_amplificacao_da_cauda,
    e04_carga_e_saturacao,
    e05_correlacao_e_trace,
    e06_caos_queda_de_replica,
    e07_caos_classes_de_erro,
)


def principal():
    for antigo in pasta_de_evidencias.glob("e*.json"):
        antigo.unlink()
    inicio = time.monotonic()
    for modulo in experimentos:
        print(f"\n=== {modulo.__name__.rsplit('.', 1)[-1]} ===")
        modulo.executar()
    aprovadas, total = gerar()
    print(f"\n{len(experimentos)} experimentos em {time.monotonic() - inicio:.0f} s; {aprovadas}/{total} verificações aprovadas")
    return 0 if aprovadas == total else 1


if __name__ == "__main__":
    sys.exit(principal())
