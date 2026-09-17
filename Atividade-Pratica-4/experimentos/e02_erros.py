from app.acervo import ISBN_INEXISTENTE
from app.cliente import Conexao
from experimentos.comum import Servidor, ident, porta_livre
from contratos import emprestimos_pb2 as pb2

CODIGO = "E02"
TITULO = "Erros de dominio traduzidos para status gRPC"
PERGUNTA = "O cliente consegue separar erro de aplicacao de indisponibilidade do servico?"

ISBN_COM_UM_EXEMPLAR = "9788526017351"
ISBN_VALIDO = "9788535910663"


def _pedido(**campos):
    base = {"isbn": ISBN_VALIDO, "leitor": "ana.souza", "dias": 7}
    base.update(campos)
    return pb2.RegistrarEmprestimoRequest(**base)


def executar(coletor):
    with Servidor(ident(CODIGO, "servidor")) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente")) as conexao:
            casos = [
                (
                    "isbn vazio",
                    "RegistrarEmprestimo",
                    _pedido(isbn=""),
                    "INVALID_ARGUMENT",
                    "isbn",
                    "Validacao explicita antes de qualquer efeito: o pedido nem chega ao repositorio.",
                ),
                (
                    "isbn com 3 digitos",
                    "RegistrarEmprestimo",
                    _pedido(isbn="123"),
                    "INVALID_ARGUMENT",
                    "isbn",
                    "Formato errado independe do estado do sistema, entao e erro do chamador.",
                ),
                (
                    "leitor fora do formato nome.sobrenome",
                    "RegistrarEmprestimo",
                    _pedido(leitor="Ana Souza"),
                    "INVALID_ARGUMENT",
                    "leitor",
                    "O contrato aceita string, mas a regra de formato e do servico, nao do .proto.",
                ),
                (
                    "dias acima do prazo maximo",
                    "RegistrarEmprestimo",
                    _pedido(dias=99),
                    "INVALID_ARGUMENT",
                    "dias",
                    "int32 no contrato nao restringe faixa; a faixa e validada no servidor.",
                ),
                (
                    "unidade desconhecida",
                    "RegistrarEmprestimo",
                    _pedido(unidade="filial"),
                    "INVALID_ARGUMENT",
                    "unidade",
                    "Campo novo da v2 tambem e validado, senao a evolucao abriria um buraco.",
                ),
                (
                    "isbn bem formado mas fora do acervo",
                    "RegistrarEmprestimo",
                    _pedido(isbn=ISBN_INEXISTENTE),
                    "NOT_FOUND",
                    "isbn",
                    "Entrada valida e entidade ausente: NOT_FOUND, nao INVALID_ARGUMENT.",
                ),
                (
                    "consulta de codigo inexistente",
                    "ConsultarEmprestimo",
                    pb2.ConsultarEmprestimoRequest(codigo="EMP-9999"),
                    "NOT_FOUND",
                    "codigo",
                    "Mesma distincao na leitura: o formato esta certo, o recurso e que nao existe.",
                ),
                (
                    "calculo de multa sem codigos",
                    "CalcularMultas",
                    pb2.CalcularMultasRequest(codigos=[]),
                    "INVALID_ARGUMENT",
                    "codigos",
                    "repeated vazio e indistinguivel de campo ausente em proto3; "
                    "a obrigatoriedade vira regra de servico.",
                ),
            ]

            for rotulo, metodo, pedido, esperado, campo, analise in casos:
                resultado = coletor.medir(
                    CODIGO, f"{metodo} — {rotulo}", 2.0, conexao.chamar(metodo, pedido, timeout=2.0),
                    analise.split(".")[0],
                )
                coletor.registrar(
                    CODIGO, f"status de: {rotulo}", esperado, resultado.status, analise
                )
                coletor.registrar(
                    CODIGO,
                    f"campo sinalizado em: {rotulo}",
                    campo,
                    resultado.campo or "(ausente)",
                    "O interceptador devolve x-campo no trailing metadata, entao o cliente "
                    "sabe o que corrigir sem fazer parsing da mensagem de erro.",
                )

            unico = conexao.chamar(
                "RegistrarEmprestimo",
                _pedido(isbn=ISBN_COM_UM_EXEMPLAR, leitor="bruno.lima", chave_idempotencia="e02-a"),
                timeout=2.0,
            )
            coletor.registrar(
                CODIGO,
                "primeiro emprestimo do unico exemplar e aceito",
                "OK",
                unico.status,
                "Macunaima tem 1 exemplar no acervo.",
            )
            esgotado = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — sem exemplar disponivel",
                2.0,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    _pedido(
                        isbn=ISBN_COM_UM_EXEMPLAR, leitor="carla.nunes", chave_idempotencia="e02-b"
                    ),
                    timeout=2.0,
                ),
                "conflito de estado",
            )
            coletor.registrar(
                CODIGO,
                "status quando o estado impede a operacao",
                "FAILED_PRECONDITION",
                esgotado.status,
                "O pedido esta correto e o livro existe; o que falha e a precondicao de "
                "estado. Repetir sem mudar o estado nao adianta.",
            )

            coletor.registrar(
                CODIGO,
                "politica de retry sugerida para FAILED_PRECONDITION",
                "corrigir a chamada, nunca repetir",
                esgotado.politica,
                "Status coerente permite que o cliente decida sozinho entre corrigir, "
                "desistir ou repetir.",
            )

            codigo_ativo = unico.resposta.emprestimo.codigo if unico.ok else "EMP-0001"
            conexao.chamar(
                "RegistrarDevolucao",
                pb2.RegistrarDevolucaoRequest(codigo=codigo_ativo),
                timeout=2.0,
            )
            repetida = coletor.medir(
                CODIGO,
                "RegistrarDevolucao — emprestimo ja devolvido",
                2.0,
                conexao.chamar(
                    "RegistrarDevolucao",
                    pb2.RegistrarDevolucaoRequest(codigo=codigo_ativo),
                    timeout=2.0,
                ),
                "operacao nao idempotente por natureza",
            )
            coletor.registrar(
                CODIGO,
                "segunda devolucao do mesmo emprestimo",
                "FAILED_PRECONDITION",
                repetida.status,
                "Devolver duas vezes nao e o mesmo que devolver uma vez: o servico recusa "
                "em vez de sobrescrever a data.",
            )

            conexao.chamar(
                "RegistrarEmprestimo", _pedido(chave_idempotencia="e02-chave"), timeout=2.0
            )
            conflito = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — chave reusada com outro pedido",
                2.0,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    _pedido(leitor="elisa.prado", chave_idempotencia="e02-chave"),
                    timeout=2.0,
                ),
                "chave de idempotencia divergente",
            )
            coletor.registrar(
                CODIGO,
                "chave de idempotencia reusada com payload diferente",
                "ALREADY_EXISTS",
                conflito.status,
                "Reaproveitar a chave com outro conteudo e erro do chamador: o servico "
                "recusa em vez de devolver silenciosamente o emprestimo antigo.",
            )

    fantasma = porta_livre()
    with Conexao(f"127.0.0.1:{fantasma}", origem=ident(CODIGO, "orfao")) as conexao:
        mascarado = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — servidor desligado, deadline curto",
            1.5,
            conexao.chamar("RegistrarEmprestimo", _pedido(), timeout=1.5),
            "nenhum processo escutando na porta",
        )
        coletor.registrar(
            CODIGO,
            "deadline curto mascara a indisponibilidade",
            "DEADLINE_EXCEEDED",
            mascarado.status,
            "Em um canal recem-aberto o gRPC leva cerca de 2 s tentando conectar antes de "
            "declarar UNAVAILABLE. Com deadline menor que isso o cliente recebe "
            "DEADLINE_EXCEEDED e perde a causa real da falha.",
        )

        indisponivel = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — servidor desligado, deadline folgado",
            5.0,
            conexao.chamar("RegistrarEmprestimo", _pedido(), timeout=5.0),
            "mesma porta vazia, deadline maior que o backoff de conexao",
        )
        coletor.registrar(
            CODIGO,
            "status com o servidor desligado",
            "UNAVAILABLE",
            indisponivel.status,
            "Nenhuma regra de negocio foi avaliada: a chamada nao chegou ao servico. "
            "Esse e o eixo que separa erro de aplicacao de falha de infraestrutura.",
        )
        coletor.registrar(
            CODIGO,
            "detalhe do UNAVAILABLE descreve o transporte",
            True,
            "failed to connect" in indisponivel.detalhe.lower(),
            f"details() devolveu {indisponivel.detalhe[:70]!r} — nenhuma mencao a isbn, "
            "leitor ou prazo, porque nada disso chegou a ser avaliado.",
            sucesso="failed to connect" in indisponivel.detalhe.lower(),
        )
        coletor.registrar(
            CODIGO,
            "politica de retry sugerida para UNAVAILABLE",
            "repetir com backoff",
            indisponivel.politica,
            "UNAVAILABLE tende a ser transitorio, mas repetir so e seguro se a operacao "
            "for idempotente — ver E06.",
        )
        coletor.registrar(
            CODIGO,
            "quantidade de status distintos observados no cenario",
            ">= 2",
            len({medicao.status for medicao in coletor.medicoes_do_cenario(CODIGO)}),
            "A AP4 exige ao menos dois status de erro; o servico usa INVALID_ARGUMENT, "
            "NOT_FOUND, FAILED_PRECONDITION, ALREADY_EXISTS e UNAVAILABLE.",
            sucesso=len({m.status for m in coletor.medicoes_do_cenario(CODIGO)}) >= 2,
        )
