import hashlib
import subprocess
from datetime import date, timedelta

from app import config
from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import PYTHON, RAIZ, Servidor, ident

CODIGO = "E01"
TITULO = "Contrato, geracao reproduzivel de stubs e fluxo unario/streaming"
PERGUNTA = "O contrato .proto descreve o servico e pode ser regenerado do zero?"

PACOTES = ("contratos", "contratos_legado", "contratos_incompativel")
METODOS_ESPERADOS = (
    "RegistrarEmprestimo",
    "ConsultarEmprestimo",
    "RegistrarDevolucao",
    "CalcularMultas",
    "ListarEmprestimos",
)


def _impressao_dos_gerados():
    impressoes = {}
    for pacote in PACOTES:
        for padrao in ("*_pb2.py", "*_pb2_grpc.py"):
            for arquivo in sorted((RAIZ / pacote).glob(padrao)):
                conteudo = arquivo.read_bytes()
                impressoes[f"{pacote}/{arquivo.name}"] = hashlib.sha256(conteudo).hexdigest()
    return impressoes


def _regenerar():
    processo = subprocess.run(
        [PYTHON, "gerar_stubs.py"], cwd=RAIZ, capture_output=True, text=True
    )
    return processo.returncode, processo.stdout.strip()


def executar(coletor):
    antes = _impressao_dos_gerados()
    retorno, _ = _regenerar()
    depois = _impressao_dos_gerados()

    coletor.registrar(
        CODIGO,
        "gerar_stubs.py conclui sem erro",
        0,
        retorno,
        "O comando apaga os arquivos gerados e chama grpc_tools.protoc de novo, "
        "entao o contrato e regeneravel do zero.",
    )
    coletor.registrar(
        CODIGO,
        "stubs regenerados sao byte a byte iguais",
        True,
        antes == depois and bool(depois),
        f"{len(depois)} arquivos gerados a partir dos .proto; mesmos hashes SHA-256 "
        "antes e depois, logo nao ha edicao manual no codigo gerado.",
        sucesso=antes == depois and bool(depois),
    )

    descritor = pb2.DESCRIPTOR
    servico = descritor.services_by_name["Emprestimos"]
    metodos = tuple(metodo.name for metodo in servico.methods)
    coletor.registrar(
        CODIGO,
        "metodos RPC publicados pelo contrato",
        len(METODOS_ESPERADOS),
        len(metodos),
        f"O servico expoe {', '.join(metodos)} — acima do minimo de tres pedido na AP4.",
    )
    coletor.registrar(
        CODIGO,
        "mensagens proprias declaradas no .proto",
        ">= 3",
        len(descritor.message_types_by_name),
        "Tipos: " + ", ".join(sorted(descritor.message_types_by_name)) + ".",
        sucesso=len(descritor.message_types_by_name) >= 3,
    )
    coletor.registrar(
        CODIGO,
        "ListarEmprestimos declarado como server streaming",
        True,
        servico.methods_by_name["ListarEmprestimos"].server_streaming,
        "Uma requisicao produz um fluxo de respostas na mesma RPC, sem abrir uma "
        "chamada por item.",
    )

    with Servidor(ident(CODIGO, "servidor")) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente")) as conexao:
            hoje = date.today()
            criacao = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo",
                3.0,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    pb2.RegistrarEmprestimoRequest(
                        isbn="9788535910663",
                        leitor="ana.souza",
                        dias=7,
                        unidade="anexo",
                        chave_idempotencia="e01-001",
                    ),
                    timeout=3.0,
                ),
                "chamada unaria de escrita",
            )
            coletor.registrar(
                CODIGO,
                "RegistrarEmprestimo devolve OK",
                "OK",
                criacao.status,
                "Chamada unaria: uma requisicao, uma resposta.",
            )

            emprestimo = criacao.resposta.emprestimo if criacao.ok else pb2.Emprestimo()
            esperado = (hoje + timedelta(days=7)).isoformat()
            coletor.registrar(
                CODIGO,
                "prazo calculado no servidor volta no campo previsto_para",
                esperado,
                emprestimo.previsto_para,
                "O servidor e dono da regra de prazo; o cliente recebe o resultado ja "
                "serializado em Protocol Buffers.",
            )
            coletor.registrar(
                CODIGO,
                "enum Situacao chega tipado no cliente",
                "SITUACAO_ATIVO",
                pb2.Situacao.Name(emprestimo.situacao),
                "O enum viaja como inteiro no fio e volta a ser simbolo no stub gerado.",
            )
            coletor.registrar(
                CODIGO,
                "campo unidade (adicionado na v2) volta preenchido",
                "anexo",
                emprestimo.unidade,
                "Campo 9 de Emprestimo, ausente no contrato legado, e usado pelo cliente novo.",
            )

            consulta = coletor.medir(
                CODIGO,
                "ConsultarEmprestimo",
                3.0,
                conexao.chamar(
                    "ConsultarEmprestimo",
                    pb2.ConsultarEmprestimoRequest(codigo=emprestimo.codigo),
                    timeout=3.0,
                ),
                "leitura do recurso recem-criado",
            )
            coletor.registrar(
                CODIGO,
                "round-trip preserva os campos do emprestimo",
                True,
                consulta.ok and consulta.resposta.emprestimo == emprestimo,
                "Serializacao e desserializacao nao perdem nem alteram campos.",
                sucesso=consulta.ok and consulta.resposta.emprestimo == emprestimo,
            )

            for indice, leitor in enumerate(("bruno.lima", "carla.nunes", "diego.matos")):
                conexao.chamar(
                    "RegistrarEmprestimo",
                    pb2.RegistrarEmprestimoRequest(
                        isbn="9788594318602",
                        leitor=leitor,
                        dias=10,
                        chave_idempotencia=f"e01-extra-{indice}",
                    ),
                    timeout=3.0,
                )

            fluxo = coletor.medir(
                CODIGO,
                "ListarEmprestimos",
                3.0,
                conexao.transmitir(
                    "ListarEmprestimos",
                    pb2.ListarEmprestimosRequest(situacao=pb2.SITUACAO_ATIVO, limite=10),
                    timeout=3.0,
                ),
                "server streaming com 4 itens",
            )
            coletor.registrar(
                CODIGO,
                "server streaming entrega todos os ativos em uma RPC",
                4,
                len(fluxo.resposta or []),
                "Quatro mensagens Emprestimo chegaram no mesmo fluxo logico, "
                "sem uma RPC por item.",
            )

            devolucao = coletor.medir(
                CODIGO,
                "RegistrarDevolucao",
                3.0,
                conexao.chamar(
                    "RegistrarDevolucao",
                    pb2.RegistrarDevolucaoRequest(
                        codigo=emprestimo.codigo,
                        devolvido_em=(hoje + timedelta(days=11)).isoformat(),
                    ),
                    timeout=3.0,
                ),
                "devolucao com 4 dias de atraso",
            )
            coletor.registrar(
                CODIGO,
                "atraso calculado na devolucao",
                4,
                devolucao.resposta.dias_de_atraso if devolucao.ok else "-",
                "Prazo de 7 dias, devolucao no 11o dia: 4 dias de atraso.",
            )
            coletor.registrar(
                CODIGO,
                "multa em double respeita o valor por dia",
                round(4 * config.VALOR_DA_MULTA_POR_DIA, 2),
                round(devolucao.resposta.multa, 2) if devolucao.ok else "-",
                f"4 dias x R$ {config.VALOR_DA_MULTA_POR_DIA:.2f} chega ao cliente como double.",
            )
