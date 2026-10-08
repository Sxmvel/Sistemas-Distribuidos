import argparse

from cliente.resiliencia import chamar_com_retry, imprimir_falha


def ler_argumentos():
    leitor = argparse.ArgumentParser(description="Chama a rota instável com retry e backoff e mostra cada tentativa.")
    leitor.add_argument("--url", default="http://127.0.0.1:8000")
    leitor.add_argument("--atraso-ms", type=int, default=0)
    leitor.add_argument("--prob-falha", type=float, default=0.5)
    leitor.add_argument("--tentativas", type=int, default=4)
    leitor.add_argument("--timeout", type=float, default=0.5)
    leitor.add_argument("--chamadas", type=int, default=5)
    return leitor.parse_args()


def principal():
    argumentos = ler_argumentos()
    destino = f"{argumentos.url}/experimento/instavel"
    parametros = {"atraso_ms": argumentos.atraso_ms, "prob_falha": argumentos.prob_falha}
    sucessos = 0

    for indice in range(1, argumentos.chamadas + 1):
        print(f"\nchamada {indice} - GET {destino} {parametros} timeout={argumentos.timeout}s")
        resultado = chamar_com_retry(
            "GET",
            destino,
            tentativas=argumentos.tentativas,
            timeout=argumentos.timeout,
            ao_falhar=imprimir_falha,
            params=parametros,
        )
        for tentativa in resultado.tentativas:
            print(
                f"  tentativa {tentativa.numero}: {tentativa.duracao_ms:7.1f} ms  "
                f"status={tentativa.status or '-':<4} tipo={tentativa.categoria}"
            )
        sucessos += resultado.ok
        print(f"  resultado final: {'sucesso' if resultado.ok else 'falha'} em {resultado.duracao_total_ms:.0f} ms")

    print(f"\n{sucessos} de {argumentos.chamadas} chamadas terminaram com sucesso.")


if __name__ == "__main__":
    principal()
