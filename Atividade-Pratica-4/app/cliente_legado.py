import argparse
import json
import sys

import grpc

from contratos_legado import emprestimos_pb2 as pb2
from contratos_legado import emprestimos_pb2_grpc as pb2_grpc

DEADLINE = 5.0


def chamar(stub, nome, pedido):
    try:
        resposta = getattr(stub, nome)(pedido, timeout=DEADLINE)
        return {"status": "OK", "resposta": resposta}
    except grpc.RpcError as erro:
        return {"status": erro.code().name, "detalhe": erro.details() or ""}


def emprestimo_como_dicionario(emprestimo):
    return {
        "codigo": emprestimo.codigo,
        "isbn": emprestimo.isbn,
        "titulo": emprestimo.titulo,
        "leitor": emprestimo.leitor,
        "previsto_para": emprestimo.previsto_para,
        "situacao": pb2.Situacao.Name(emprestimo.situacao),
    }


def main(entrada=None):
    analisador = argparse.ArgumentParser(
        description="Cliente construido com os stubs do contrato anterior (sem o campo unidade)"
    )
    analisador.add_argument("--endereco", required=True)
    analisador.add_argument("--codigo-existente", required=True)
    analisador.add_argument("--isbn", default="9788594318602")
    analisador.add_argument("--leitor", default="felipe.rocha")
    opcoes = analisador.parse_args(entrada)

    relatorio = {
        "campos_de_emprestimo": sorted(
            campo.name for campo in pb2.Emprestimo.DESCRIPTOR.fields
        ),
        "campos_do_pedido": sorted(
            campo.name for campo in pb2.RegistrarEmprestimoRequest.DESCRIPTOR.fields
        ),
    }

    with grpc.insecure_channel(opcoes.endereco) as canal:
        stub = pb2_grpc.EmprestimosStub(canal)

        escrita = chamar(
            stub,
            "RegistrarEmprestimo",
            pb2.RegistrarEmprestimoRequest(
                isbn=opcoes.isbn,
                leitor=opcoes.leitor,
                dias=7,
                chave_idempotencia="e07-legado",
            ),
        )
        relatorio["escrita_status"] = escrita["status"]
        if escrita["status"] == "OK":
            relatorio["escrita"] = emprestimo_como_dicionario(
                escrita["resposta"].emprestimo
            )
            relatorio["escrita_reaproveitado"] = escrita["resposta"].reaproveitado

        leitura = chamar(
            stub,
            "ConsultarEmprestimo",
            pb2.ConsultarEmprestimoRequest(codigo=opcoes.codigo_existente),
        )
        relatorio["leitura_status"] = leitura["status"]
        if leitura["status"] == "OK":
            emprestimo = leitura["resposta"].emprestimo
            relatorio["leitura"] = emprestimo_como_dicionario(emprestimo)
            bytes_reserializados = emprestimo.SerializeToString()
            relatorio["bytes_reserializados"] = bytes_reserializados.hex()
            relatorio["tamanho_reserializado"] = len(bytes_reserializados)

        try:
            fluxo = list(
                stub.ListarEmprestimos(
                    pb2.ListarEmprestimosRequest(situacao=pb2.SITUACAO_ATIVO, limite=20),
                    timeout=DEADLINE,
                )
            )
            relatorio["streaming_status"] = "OK"
            relatorio["streaming_itens"] = len(fluxo)
        except grpc.RpcError as erro:
            relatorio["streaming_status"] = erro.code().name

        invalido = chamar(
            stub,
            "RegistrarEmprestimo",
            pb2.RegistrarEmprestimoRequest(isbn="123", leitor=opcoes.leitor, dias=7),
        )
        relatorio["invalido_status"] = invalido["status"]
        relatorio["invalido_detalhe"] = invalido.get("detalhe", "")

    json.dump(relatorio, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
