import json
import subprocess

from app.cliente import Conexao
from contratos import emprestimos_pb2 as pb2
from experimentos.comum import PYTHON, RAIZ, Servidor, ident

CODIGO = "E07"
TITULO = "Evolucao do contrato: cliente antigo contra servidor novo"
PERGUNTA = "Quais mudancas no .proto preservam clientes antigos e quais corrompem dados?"

CAMPO_NOVO = "unidade"
UNIDADE_ESCOLHIDA = "anexo"
ISBN = "9788594318602"


def _executar(modulo, *argumentos):
    processo = subprocess.run(
        [PYTHON, "-m", modulo, *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if processo.returncode != 0:
        return {"erro": processo.stderr.strip()[-400:]}
    return json.loads(processo.stdout)


def _tentar_importar_as_duas_versoes():
    processo = subprocess.run(
        [
            PYTHON,
            "-c",
            "from contratos import emprestimos_pb2 as a;"
            "from contratos_legado import emprestimos_pb2 as b;"
            "print('coexistiram')",
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return processo.returncode, (processo.stdout + processo.stderr).strip()


def executar(coletor):
    with Servidor(ident(CODIGO, "servidor")) as servidor:
        with Conexao(servidor.endereco, origem=ident(CODIGO, "cliente-novo")) as conexao:
            criacao = coletor.medir(
                CODIGO,
                "RegistrarEmprestimo — cliente novo usa o campo unidade",
                5.0,
                conexao.chamar(
                    "RegistrarEmprestimo",
                    pb2.RegistrarEmprestimoRequest(
                        isbn=ISBN,
                        leitor="gabriela.dias",
                        dias=7,
                        unidade=UNIDADE_ESCOLHIDA,
                        chave_idempotencia="e07-novo",
                    ),
                    timeout=5.0,
                ),
                "contrato v2 dos dois lados",
            )
            coletor.registrar(
                CODIGO,
                "cliente novo grava o campo adicionado na v2",
                UNIDADE_ESCOLHIDA,
                criacao.resposta.emprestimo.unidade if criacao.ok else "-",
                "Campo 5 no pedido e campo 9 na resposta, ambos ausentes no contrato anterior.",
            )
            emprestimo = criacao.resposta.emprestimo
            codigo_existente = emprestimo.codigo
            hex_do_emprestimo = emprestimo.SerializeToString().hex()
            hex_do_pedido = pb2.RegistrarEmprestimoRequest(
                isbn=ISBN, leitor="gabriela.dias", dias=7, unidade=UNIDADE_ESCOLHIDA
            ).SerializeToString().hex()

        relatorio = _executar(
            "app.cliente_legado",
            "--endereco",
            servidor.endereco,
            "--codigo-existente",
            codigo_existente,
        )

    if "erro" in relatorio:
        coletor.registrar(
            CODIGO,
            "cliente legado executa",
            "sem erro",
            relatorio["erro"][:80],
            "O subprocesso do cliente legado falhou.",
            sucesso=False,
        )
        return

    coletor.registrar(
        CODIGO,
        "stubs legados nao conhecem o campo unidade",
        False,
        CAMPO_NOVO in relatorio["campos_de_emprestimo"],
        "Campos vistos pelo cliente antigo: "
        + ", ".join(relatorio["campos_de_emprestimo"])
        + ".",
    )
    coletor.registrar(
        CODIGO,
        "pedido legado tambem nao tem o campo unidade",
        False,
        CAMPO_NOVO in relatorio["campos_do_pedido"],
        "O cliente antigo nem sabe que existe o campo; ele nao e obrigado a enviar nada.",
    )
    coletor.registrar(
        CODIGO,
        "escrita do cliente antigo no servidor novo",
        "OK",
        relatorio["escrita_status"],
        "Adicionar um campo opcional nao quebra quem foi compilado antes: o servidor "
        "recebe o campo ausente com o valor padrao e aplica o default do dominio.",
    )
    coletor.registrar(
        CODIGO,
        "leitura do cliente antigo de um recurso criado pelo cliente novo",
        "OK",
        relatorio["leitura_status"],
        "A resposta traz o campo 9, que o stub antigo simplesmente ignora.",
    )
    coletor.registrar(
        CODIGO,
        "campos conhecidos chegam corretos ao cliente antigo",
        "gabriela.dias",
        relatorio.get("leitura", {}).get("leitor", "-"),
        "Os numeros de campo nao mudaram, entao cada valor continua caindo no campo certo.",
    )
    reserializados = relatorio.get("bytes_reserializados", "")
    coletor.registrar(
        CODIGO,
        "cliente antigo preserva o campo desconhecido ao reserializar",
        True,
        reserializados == hex_do_emprestimo,
        "O stub antigo guarda o campo 9 como unknown field e devolve os mesmos "
        f"{len(hex_do_emprestimo) // 2} bytes, terminados em "
        f"`...{hex_do_emprestimo[-14:]}` (campo 9 = 'anexo'). Um proxy compilado com o "
        "contrato velho nao apaga dados do contrato novo.",
        sucesso=reserializados == hex_do_emprestimo,
    )
    coletor.registrar(
        CODIGO,
        "server streaming continua funcionando para o cliente antigo",
        "OK",
        relatorio.get("streaming_status", "-"),
        f"O fluxo entregou {relatorio.get('streaming_itens', 0)} itens usando os stubs antigos.",
    )
    coletor.registrar(
        CODIGO,
        "modelo de erro permanece o mesmo para o cliente antigo",
        "INVALID_ARGUMENT",
        relatorio.get("invalido_status", "-"),
        "Status e mensagens nao dependem da versao do stub: "
        f"{relatorio.get('invalido_detalhe', '')[:60]!r}.",
    )

    incompativel = _executar(
        "app.inspetor_incompativel",
        "--emprestimo-hex",
        hex_do_emprestimo,
        "--pedido-hex",
        hex_do_pedido,
    )

    if "erro" not in incompativel:
        leitura = incompativel["emprestimo"]
        coletor.registrar(
            CODIGO,
            "reuso do numero de campo 4 nao gera erro de parsing",
            "parseou",
            leitura["resultado"],
            "Trocar leitor por unidade no campo 4 mantem o mesmo wire type, entao o parser "
            "aceita os bytes sem reclamar.",
        )
        coletor.registrar(
            CODIGO,
            "reuso do numero de campo 4 corrompe o dado em silencio",
            "gabriela.dias",
            leitura["unidade"],
            "O leitor virou unidade. Nao houve excecao, log nem status de erro: a mudanca "
            "incompativel mais perigosa e a que continua parseando.",
        )
        pedido = incompativel["pedido"]
        coletor.registrar(
            CODIGO,
            "troca de tipo no campo 3 tambem nao levanta excecao",
            "parseou",
            pedido["resultado"],
            "int32 dias virou string dias: o wire type nao bate e o valor e descartado "
            "como campo desconhecido.",
        )
        coletor.registrar(
            CODIGO,
            "troca de tipo no campo 3 perde o valor enviado",
            "",
            pedido["dias"],
            "O cliente enviou 7 dias e o leitor com o esquema alterado enxerga string vazia. "
            "Perda silenciosa de dado.",
        )

    retorno, saida = _tentar_importar_as_duas_versoes()
    coletor.registrar(
        CODIGO,
        "duas versoes do mesmo package no mesmo processo",
        "falha",
        "falha" if retorno != 0 else "coexistiram",
        "O descriptor pool do protobuf recusa simbolos duplicados: "
        f"{saida.splitlines()[-1][:100] if saida else ''}. Por isso o cliente legado roda "
        "como processo separado, que e tambem como a migracao acontece na pratica.",
        sucesso=retorno != 0,
    )
