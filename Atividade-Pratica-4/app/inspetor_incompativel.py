import argparse
import json
import sys

from contratos_incompativel import emprestimos_pb2 as pb2


def ler_emprestimo(bruto):
    emprestimo = pb2.Emprestimo()
    try:
        emprestimo.ParseFromString(bruto)
    except Exception as erro:
        return {"resultado": "erro", "excecao": type(erro).__name__, "detalhe": str(erro)[:160]}
    return {
        "resultado": "parseou",
        "codigo": emprestimo.codigo,
        "isbn": emprestimo.isbn,
        "titulo": emprestimo.titulo,
        "unidade": emprestimo.unidade,
        "bytes_reserializados": emprestimo.SerializeToString().hex(),
    }


def ler_pedido(bruto):
    pedido = pb2.RegistrarEmprestimoRequest()
    try:
        pedido.ParseFromString(bruto)
    except Exception as erro:
        return {"resultado": "erro", "excecao": type(erro).__name__, "detalhe": str(erro)[:160]}
    try:
        dias = pedido.dias
    except UnicodeDecodeError as erro:
        return {
            "resultado": "erro-na-leitura",
            "excecao": type(erro).__name__,
            "detalhe": str(erro)[:160],
        }
    return {
        "resultado": "parseou",
        "isbn": pedido.isbn,
        "leitor": pedido.leitor,
        "dias": dias,
    }


def main(entrada=None):
    analisador = argparse.ArgumentParser(
        description="Le bytes do contrato v2 usando um esquema com mudancas incompativeis"
    )
    analisador.add_argument("--emprestimo-hex", required=True)
    analisador.add_argument("--pedido-hex", required=True)
    opcoes = analisador.parse_args(entrada)

    relatorio = {
        "emprestimo": ler_emprestimo(bytes.fromhex(opcoes.emprestimo_hex)),
        "pedido": ler_pedido(bytes.fromhex(opcoes.pedido_hex)),
    }
    json.dump(relatorio, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
