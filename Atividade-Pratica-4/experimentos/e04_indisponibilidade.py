import threading
import time

from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import Servidor, ident

CODIGO = "E04"
TITULO = "Indisponibilidade do servidor durante o uso do cliente"
PERGUNTA = "O cliente distingue 'o servico recusou' de 'o servico nao respondeu'?"

PEDIDO_VALIDO = pb2.RegistrarEmprestimoRequest(
    isbn="9788594318602", leitor="ana.souza", dias=7
)
PEDIDO_INVALIDO = pb2.RegistrarEmprestimoRequest(isbn="123", leitor="ana.souza", dias=7)


def executar(coletor):
    servidor = Servidor(ident(CODIGO, "servidor"), semear=2)
    servidor.iniciar()

    with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente")) as conexao:
        no_ar = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — pedido valido, servidor no ar",
            2.0,
            conexao.chamar("RegistrarEmprestimo", PEDIDO_VALIDO, timeout=2.0),
            "linha de base",
        )
        invalido_no_ar = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — pedido invalido, servidor no ar",
            2.0,
            conexao.chamar("RegistrarEmprestimo", PEDIDO_INVALIDO, timeout=2.0),
            "validacao executada pelo servico",
        )
        coletor.registrar(
            CODIGO,
            "pedido valido com o servidor no ar",
            "OK",
            no_ar.status,
            "Estado inicial do experimento.",
        )
        coletor.registrar(
            CODIGO,
            "pedido invalido com o servidor no ar",
            "INVALID_ARGUMENT",
            invalido_no_ar.status,
            "O servico recebeu, avaliou e recusou. Ha uma decisao de dominio por tras "
            "do status, e ela veio com a mensagem de erro.",
        )

        servidor.parar()

        fora = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — pedido valido, servidor fora",
            5.0,
            conexao.chamar("RegistrarEmprestimo", PEDIDO_VALIDO, timeout=5.0),
            "sem processo escutando",
        )
        invalido_fora = coletor.medir(
            CODIGO,
            "RegistrarEmprestimo — pedido invalido, servidor fora",
            5.0,
            conexao.chamar("RegistrarEmprestimo", PEDIDO_INVALIDO, timeout=5.0),
            "mesmo pedido invalido de antes",
        )
        coletor.registrar(
            CODIGO,
            "pedido valido com o servidor fora",
            "UNAVAILABLE",
            fora.status,
            "O canal nao conseguiu entregar a chamada. Nada foi executado no servidor.",
        )
        coletor.registrar(
            CODIGO,
            "pedido invalido com o servidor fora",
            "UNAVAILABLE",
            invalido_fora.status,
            "O mesmo pedido que antes devolvia INVALID_ARGUMENT agora devolve UNAVAILABLE: "
            "sem servidor nao existe validacao, e a falha e do transporte.",
        )
        coletor.registrar(
            CODIGO,
            "UNAVAILABLE chega antes de esgotar o deadline de 5 s",
            "< 5000 ms",
            fora.latencia_ms,
            "O cliente nao fica preso ate o fim do deadline: ele desiste quando as "
            "tentativas de conexao falham. Mas isso leva alguns segundos, entao um deadline "
            "curto devolveria DEADLINE_EXCEEDED em vez da causa real.",
            sucesso=fora.latencia_ms < 5000,
        )
        coletor.registrar(
            CODIGO,
            "detalhe do erro descreve transporte, nao dominio",
            True,
            "connect" in fora.detalhe.lower() or "unavailable" in fora.detalhe.lower(),
            f"details() devolveu: {fora.detalhe[:90]!r}",
            sucesso="connect" in fora.detalhe.lower()
            or "unavailable" in fora.detalhe.lower(),
        )

        espera = {}

        def chamar_esperando():
            espera["resultado"] = conexao.chamar(
                "RegistrarEmprestimo",
                PEDIDO_VALIDO,
                timeout=20.0,
                esperar_disponivel=True,
            )

        linha = threading.Thread(target=chamar_esperando, daemon=True)
        linha.start()
        time.sleep(1.0)
        servidor.iniciar()
        linha.join(25)

        resultado_da_espera = espera.get("resultado")
        coletor.registrar(
            CODIGO,
            "chamada com wait_for_ready sobrevive a queda do servidor",
            "OK",
            resultado_da_espera.status if resultado_da_espera else "sem retorno",
            "Com wait_for_ready o cliente segura a chamada ate o canal reconectar, em vez "
            "de receber UNAVAILABLE. Isso substitui o retry manual, mas so e seguro "
            "dentro do deadline e para operacoes que toleram repeticao.",
        )
        if resultado_da_espera:
            coletor.anotar_medicao(
                CODIGO,
                "RegistrarEmprestimo — wait_for_ready durante a queda",
                20.0,
                resultado_da_espera.status,
                resultado_da_espera.latencia_ms,
                "servidor voltou ~1 s depois",
            )
            coletor.registrar(
                CODIGO,
                "a espera cobre o tempo que o servidor ficou fora",
                "> 900 ms",
                resultado_da_espera.latencia_ms,
                "A latencia observada inclui a janela de indisponibilidade, entao o custo "
                "da resiliencia aparece no tempo de resposta.",
                sucesso=resultado_da_espera.latencia_ms > 900,
            )

        demorada = {}

        def chamar_demorada():
            demorada["resultado"] = conexao.chamar(
                "CalcularMultas",
                pb2.CalcularMultasRequest(codigos=["EMP-0001"] * 60),
                timeout=10.0,
            )

        linha = threading.Thread(target=chamar_demorada, daemon=True)
        linha.start()
        time.sleep(0.6)
        servidor.matar()
        linha.join(20)

        queda = demorada.get("resultado")
        coletor.registrar(
            CODIGO,
            "servidor morto no meio da chamada",
            "UNAVAILABLE",
            queda.status if queda else "sem retorno",
            "O processo foi morto com o trabalho em andamento. O cliente descobre pela "
            "queda da conexao, nao por uma resposta do servico — e nao sabe quanto do "
            "trabalho ja tinha efeito.",
        )
        if queda:
            coletor.anotar_medicao(
                CODIGO,
                "CalcularMultas — servidor morto no meio",
                10.0,
                queda.status,
                queda.latencia_ms,
                "processo encerrado com kill apos ~0,6 s",
            )
