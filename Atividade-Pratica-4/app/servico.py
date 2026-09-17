import time
from datetime import date

from app import config, dominio
from app.dominio import EntradaInvalida
from app.erros import ChamadaAbandonada
from app.repositorio import Repositorio
from contratos import emprestimos_pb2 as pb2
from contratos import emprestimos_pb2_grpc as pb2_grpc

SITUACAO_PARA_PROTO = {
    dominio.ATIVO: pb2.SITUACAO_ATIVO,
    dominio.DEVOLVIDO: pb2.SITUACAO_DEVOLVIDO,
}

SITUACAO_DO_PROTO = {
    pb2.SITUACAO_ATIVO: dominio.ATIVO,
    pb2.SITUACAO_DEVOLVIDO: dominio.DEVOLVIDO,
}


def para_proto(emprestimo):
    return pb2.Emprestimo(
        codigo=emprestimo.codigo,
        isbn=emprestimo.isbn,
        titulo=emprestimo.titulo,
        leitor=emprestimo.leitor,
        emprestado_em=emprestimo.emprestado_em.isoformat(),
        previsto_para=emprestimo.previsto_para.isoformat(),
        devolvido_em=emprestimo.devolvido_em.isoformat() if emprestimo.devolvido_em else "",
        situacao=SITUACAO_PARA_PROTO[emprestimo.situacao],
        unidade=emprestimo.unidade,
    )


class ServicoDeEmprestimos(pb2_grpc.EmprestimosServicer):
    def __init__(self, repositorio=None, custo_por_codigo=None, atraso_na_escrita=0.0):
        self.repositorio = repositorio or Repositorio()
        self.custo_por_codigo = (
            config.CUSTO_POR_CODIGO_NA_MULTA if custo_por_codigo is None else custo_por_codigo
        )
        self.atraso_na_escrita = atraso_na_escrita

    def RegistrarEmprestimo(self, pedido, contexto):
        isbn = dominio.validar_isbn(pedido.isbn)
        leitor = dominio.validar_leitor(pedido.leitor)
        dias = dominio.validar_dias(pedido.dias)
        unidade = dominio.validar_unidade(pedido.unidade)
        chave = (pedido.chave_idempotencia or "").strip()

        emprestimo, reaproveitado, disponiveis = self.repositorio.registrar(
            isbn, leitor, dias, unidade, chave
        )
        if self.atraso_na_escrita:
            time.sleep(self.atraso_na_escrita)
        return pb2.RegistrarEmprestimoResponse(
            emprestimo=para_proto(emprestimo),
            reaproveitado=reaproveitado,
            exemplares_disponiveis=disponiveis,
        )

    def ConsultarEmprestimo(self, pedido, contexto):
        codigo = dominio.validar_codigo(pedido.codigo)
        emprestimo = self.repositorio.consultar(codigo)
        return pb2.ConsultarEmprestimoResponse(emprestimo=para_proto(emprestimo))

    def RegistrarDevolucao(self, pedido, contexto):
        codigo = dominio.validar_codigo(pedido.codigo)
        devolvido_em = dominio.validar_data(pedido.devolvido_em, "devolvido_em")
        emprestimo = self.repositorio.devolver(codigo, devolvido_em)
        referencia = emprestimo.devolvido_em or date.today()
        return pb2.RegistrarDevolucaoResponse(
            emprestimo=para_proto(emprestimo),
            dias_de_atraso=emprestimo.dias_de_atraso(referencia),
            multa=emprestimo.multa(referencia),
        )

    def CalcularMultas(self, pedido, contexto):
        codigos = [(item or "").strip().upper() for item in pedido.codigos]
        codigos = [item for item in codigos if item]
        if not codigos:
            raise EntradaInvalida("codigos não pode ser vazio", "codigos")
        if len(codigos) > config.LIMITE_DE_CODIGOS_NA_MULTA:
            raise EntradaInvalida(
                f"codigos aceita no máximo {config.LIMITE_DE_CODIGOS_NA_MULTA} itens",
                "codigos",
            )
        referencia = dominio.validar_data(pedido.referencia, "referencia") or date.today()

        itens = []
        total = 0.0
        for posicao, codigo in enumerate(codigos):
            if not contexto.is_active():
                raise ChamadaAbandonada(posicao, len(codigos))
            time.sleep(self.custo_por_codigo)
            emprestimo = self.repositorio.consultar(codigo)
            multa = emprestimo.multa(referencia)
            total += multa
            itens.append(
                pb2.MultaDoEmprestimo(
                    codigo=emprestimo.codigo,
                    dias_de_atraso=emprestimo.dias_de_atraso(referencia),
                    multa=multa,
                )
            )

        return pb2.CalcularMultasResponse(
            itens=itens, total=round(total, 2), quantidade=len(itens)
        )

    def ListarEmprestimos(self, pedido, contexto):
        leitor = dominio.validar_leitor(pedido.leitor) if pedido.leitor else None
        situacao = SITUACAO_DO_PROTO.get(pedido.situacao)
        limite = pedido.limite or config.LIMITE_PADRAO_DA_LISTAGEM
        if limite < 0:
            raise EntradaInvalida("limite não pode ser negativo", "limite")

        for emprestimo in self.repositorio.listar(leitor, situacao, limite):
            if not contexto.is_active():
                return
            yield para_proto(emprestimo)
