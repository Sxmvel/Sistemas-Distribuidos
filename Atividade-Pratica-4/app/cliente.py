import argparse
import time
from dataclasses import dataclass, field

import grpc

from app import config
from app.erros import politica_de_retry
from app.interceptadores import InterceptadorDoCliente, Metricas
from app.registro import Registrador
from app.servidor import OPCOES_DO_CANAL
from contratos import emprestimos_pb2 as pb2
from contratos import emprestimos_pb2_grpc as pb2_grpc


@dataclass
class Resultado:
    metodo: str
    status: str
    latencia_ms: float
    resposta: object = None
    detalhe: str = ""
    campo: str = ""
    metadados: dict = field(default_factory=dict)

    @property
    def ok(self):
        return self.status == grpc.StatusCode.OK.name

    @property
    def politica(self):
        return politica_de_retry(self.status)


def metadados_de(erro):
    try:
        return {chave: valor for chave, valor in erro.trailing_metadata() or ()}
    except (AttributeError, TypeError):
        return {}


class Conexao:
    def __init__(self, endereco=None, origem="cliente", registrador=None, silencioso=True):
        self.endereco = endereco or f"{config.SERVIDOR_HOST}:{config.SERVIDOR_PORTA}"
        self.registrador = registrador or Registrador(origem, "cliente", silencioso=silencioso)
        self.metricas = Metricas()
        self.interceptador = InterceptadorDoCliente(
            self.registrador, origem, self.metricas
        )
        self._canal = None
        self.stub = None

    def abrir(self):
        bruto = grpc.insecure_channel(self.endereco, options=OPCOES_DO_CANAL)
        self._canal = grpc.intercept_channel(bruto, self.interceptador)
        self.stub = pb2_grpc.EmprestimosStub(self._canal)
        return self

    def fechar(self):
        if self._canal is not None:
            self._canal.close()
            self._canal = None
        self.registrador.fechar()

    def __enter__(self):
        return self.abrir()

    def __exit__(self, *_):
        self.fechar()

    def chamar(
        self,
        nome,
        pedido,
        timeout=config.DEADLINE_PADRAO,
        metadados=None,
        esperar_disponivel=False,
    ):
        metodo = getattr(self.stub, nome)
        inicio = time.perf_counter()
        try:
            resposta = metodo(
                pedido,
                timeout=timeout,
                metadata=metadados,
                wait_for_ready=esperar_disponivel,
            )
            latencia = (time.perf_counter() - inicio) * 1000
            return Resultado(nome, grpc.StatusCode.OK.name, latencia, resposta)
        except grpc.RpcError as erro:
            latencia = (time.perf_counter() - inicio) * 1000
            extras = metadados_de(erro)
            return Resultado(
                nome,
                erro.code().name,
                latencia,
                detalhe=erro.details() or "",
                campo=extras.get("x-campo", ""),
                metadados=extras,
            )

    def transmitir(self, nome, pedido, timeout=config.DEADLINE_PADRAO):
        metodo = getattr(self.stub, nome)
        inicio = time.perf_counter()
        recebidos = []
        try:
            for item in metodo(pedido, timeout=timeout):
                recebidos.append(item)
            latencia = (time.perf_counter() - inicio) * 1000
            return Resultado(nome, grpc.StatusCode.OK.name, latencia, recebidos)
        except grpc.RpcError as erro:
            latencia = (time.perf_counter() - inicio) * 1000
            return Resultado(
                nome,
                erro.code().name,
                latencia,
                recebidos,
                detalhe=erro.details() or "",
                campo=metadados_de(erro).get("x-campo", ""),
            )


def linha(rotulo, resultado):
    detalhe = f" — {resultado.detalhe}" if resultado.detalhe else ""
    return (
        f"{rotulo:<46} {resultado.status:<20} {resultado.latencia_ms:7.1f} ms"
        f"{detalhe}"
    )


def demonstrar(conexao, deadline_curto, deadline_longo):
    print(f"{'chamada':<46} {'status':<20} {'latência':>10}")
    print("-" * 96)

    criacao = conexao.chamar(
        "RegistrarEmprestimo",
        pb2.RegistrarEmprestimoRequest(
            isbn="9788535910663",
            leitor="ana.souza",
            dias=7,
            unidade="central",
            chave_idempotencia="demo-001",
        ),
        timeout=deadline_longo,
    )
    print(linha("RegistrarEmprestimo (válido)", criacao))
    codigo = criacao.resposta.emprestimo.codigo if criacao.ok else ""

    repetida = conexao.chamar(
        "RegistrarEmprestimo",
        pb2.RegistrarEmprestimoRequest(
            isbn="9788535910663",
            leitor="ana.souza",
            dias=7,
            unidade="central",
            chave_idempotencia="demo-001",
        ),
        timeout=deadline_longo,
    )
    reaproveitado = repetida.ok and repetida.resposta.reaproveitado
    print(linha(f"RegistrarEmprestimo (retry, reaproveitado={reaproveitado})", repetida))

    invalido = conexao.chamar(
        "RegistrarEmprestimo",
        pb2.RegistrarEmprestimoRequest(isbn="123", leitor="ana.souza", dias=7),
        timeout=deadline_longo,
    )
    print(linha("RegistrarEmprestimo (isbn inválido)", invalido))

    ausente = conexao.chamar(
        "ConsultarEmprestimo",
        pb2.ConsultarEmprestimoRequest(codigo="EMP-9999"),
        timeout=deadline_longo,
    )
    print(linha("ConsultarEmprestimo (inexistente)", ausente))

    listagem = conexao.transmitir(
        "ListarEmprestimos",
        pb2.ListarEmprestimosRequest(situacao=pb2.SITUACAO_ATIVO, limite=10),
        timeout=deadline_longo,
    )
    recebidos = len(listagem.resposta or [])
    print(linha(f"ListarEmprestimos (stream, {recebidos} itens)", listagem))

    codigos = [codigo or "EMP-0001"] * 40
    curto = conexao.chamar(
        "CalcularMultas",
        pb2.CalcularMultasRequest(codigos=codigos),
        timeout=deadline_curto,
    )
    print(linha(f"CalcularMultas (deadline {deadline_curto}s)", curto))
    print(f"{'':46} política sugerida: {curto.politica}")

    longo = conexao.chamar(
        "CalcularMultas",
        pb2.CalcularMultasRequest(codigos=codigos),
        timeout=deadline_longo,
    )
    print(linha(f"CalcularMultas (deadline {deadline_longo}s)", longo))


def argumentos(entrada=None):
    analisador = argparse.ArgumentParser(description="Cliente gRPC de empréstimos")
    analisador.add_argument("--host", default=config.SERVIDOR_HOST)
    analisador.add_argument("--porta", type=int, default=config.SERVIDOR_PORTA)
    analisador.add_argument("--id", default="cliente")
    analisador.add_argument("--deadline-curto", type=float, default=0.3)
    analisador.add_argument("--deadline-longo", type=float, default=3.0)
    analisador.add_argument("--silencioso", action="store_true")
    return analisador.parse_args(entrada)


def main(entrada=None):
    opcoes = argumentos(entrada)
    endereco = f"{opcoes.host}:{opcoes.porta}"
    print(f"conectando em {endereco}\n")
    with Conexao(endereco, origem=opcoes.id, silencioso=opcoes.silencioso) as conexao:
        demonstrar(conexao, opcoes.deadline_curto, opcoes.deadline_longo)
        por_metodo, por_status = conexao.metricas.resumo()
    print("\nstatus observados:", por_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
