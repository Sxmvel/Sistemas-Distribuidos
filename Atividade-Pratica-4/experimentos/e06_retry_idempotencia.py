from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import (
    Servidor,
    chamadas_concluidas,
    esperar_ate,
    ident,
)

CODIGO = "E06"
TITULO = "Retry apos deadline ambiguo, com e sem chave de idempotencia"
PERGUNTA = "Como repetir uma chamada sem duplicar o efeito que talvez ja tenha acontecido?"

ATRASO_NA_ESCRITA = 0.5
DEADLINE_CURTO = 0.15
DEADLINE_FOLGADO = 5.0
ISBN = "9788594318602"


def _pedido(leitor, chave=""):
    return pb2.RegistrarEmprestimoRequest(
        isbn=ISBN, leitor=leitor, dias=7, chave_idempotencia=chave
    )


def _ativos_do_leitor(conexao, leitor):
    resultado = conexao.transmitir(
        "ListarEmprestimos",
        pb2.ListarEmprestimosRequest(leitor=leitor, situacao=pb2.SITUACAO_ATIVO, limite=50),
        timeout=DEADLINE_FOLGADO,
    )
    return [item for item in (resultado.resposta or []) if item.isbn == ISBN]


def executar(coletor):
    identificador = ident(CODIGO, "servidor")
    with Servidor(identificador, atraso_na_escrita=ATRASO_NA_ESCRITA) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente")) as conexao:
            sem_chave = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — 1a tentativa sem chave",
                DEADLINE_CURTO,
                conexao.chamar("RegistrarEmprestimo", _pedido("ana.souza"), timeout=DEADLINE_CURTO),
                f"servidor leva {ATRASO_NA_ESCRITA:g} s para responder a escrita",
            )
            coletor.registrar(
                CODIGO,
                "cliente desiste antes da resposta da escrita",
                "DEADLINE_EXCEEDED",
                sem_chave.status,
                "O deadline estourou depois que o repositorio ja tinha gravado. O cliente "
                "nao tem como saber disso pelo status.",
            )

            esperar_ate(
                lambda: len(
                    chamadas_concluidas(identificador, "RegistrarEmprestimo", "OK")
                )
                >= 1,
                limite=10,
            )
            concluidas = chamadas_concluidas(identificador, "RegistrarEmprestimo", "OK")
            coletor.registrar(
                CODIGO,
                "servidor concluiu a chamada que o cliente deu por perdida",
                ">= 1",
                len(concluidas),
                "O interceptador do servidor registrou status OK para a mesma chamada que "
                "o cliente contabilizou como DEADLINE_EXCEEDED. E exatamente a ambiguidade "
                "da secao 6.10: o status nao fala sobre efeitos ja executados.",
                sucesso=len(concluidas) >= 1,
            )

            depois_da_primeira = _ativos_do_leitor(conexao, "ana.souza")
            coletor.registrar(
                CODIGO,
                "efeito aplicado apesar do erro visto pelo cliente",
                1,
                len(depois_da_primeira),
                "Uma consulta posterior mostra o emprestimo criado: o trabalho aconteceu, "
                "so a resposta nao chegou a tempo.",
            )

            coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — retry cego sem chave",
                DEADLINE_FOLGADO,
                conexao.chamar(
                    "RegistrarEmprestimo", _pedido("ana.souza"), timeout=DEADLINE_FOLGADO
                ),
                "retry ingenuo do mesmo pedido",
            )
            depois_do_retry = _ativos_do_leitor(conexao, "ana.souza")
            coletor.registrar(
                CODIGO,
                "retry sem chave duplica o emprestimo",
                2,
                len(depois_do_retry),
                "O mesmo leitor terminou com dois emprestimos do mesmo titulo e dois "
                "exemplares reservados. O retry foi seguro para a rede e destrutivo para "
                "o dominio.",
            )
            coletor.registrar(
                CODIGO,
                "codigos gerados no retry sem chave sao distintos",
                2,
                len({item.codigo for item in depois_do_retry}),
                "Sem chave o servico nao tem como reconhecer a repeticao: cada chamada e "
                "um pedido novo.",
            )

            chave = "e06-idempotente"
            com_chave = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — 1a tentativa com chave",
                DEADLINE_CURTO,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    _pedido("bruno.lima", chave),
                    timeout=DEADLINE_CURTO,
                ),
                "mesma janela de ambiguidade",
            )
            coletor.registrar(
                CODIGO,
                "primeira tentativa com chave tambem estoura o deadline",
                "DEADLINE_EXCEEDED",
                com_chave.status,
                "A chave nao torna a chamada mais rapida: ela so muda o que acontece no "
                "reenvio.",
            )

            reenvio = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — retry com a mesma chave",
                DEADLINE_FOLGADO,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    _pedido("bruno.lima", chave),
                    timeout=DEADLINE_FOLGADO,
                ),
                "retry protegido por chave de idempotencia",
            )
            coletor.registrar(
                CODIGO,
                "retry com chave devolve OK",
                "OK",
                reenvio.status,
                "O servico reconhece a chave e devolve o resultado da primeira execucao.",
            )
            coletor.registrar(
                CODIGO,
                "resposta marca que o resultado foi reaproveitado",
                True,
                reenvio.ok and reenvio.resposta.reaproveitado,
                "O campo reaproveitado avisa o cliente que nao houve efeito novo — "
                "informacao que um simples OK esconderia.",
                sucesso=reenvio.ok and reenvio.resposta.reaproveitado,
            )

            com_chave_final = _ativos_do_leitor(conexao, "bruno.lima")
            coletor.registrar(
                CODIGO,
                "retry com chave nao duplica o emprestimo",
                1,
                len(com_chave_final),
                "Mesmo com duas chamadas na rede, o dominio registrou um unico emprestimo. "
                "E assim que DEADLINE_EXCEEDED deixa de ser perigoso para uma operacao "
                "de escrita.",
            )

            conflito = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — mesma chave, outro pedido",
                DEADLINE_FOLGADO,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    _pedido("carla.nunes", chave),
                    timeout=DEADLINE_FOLGADO,
                ),
                "chave reaproveitada indevidamente",
            )
            coletor.registrar(
                CODIGO,
                "chave so vale para o pedido original",
                "ALREADY_EXISTS",
                conflito.status,
                "A chave guarda a impressao do pedido. Reusar a chave com outro conteudo e "
                "bug do cliente, e o servico recusa em vez de devolver o recurso errado.",
            )
