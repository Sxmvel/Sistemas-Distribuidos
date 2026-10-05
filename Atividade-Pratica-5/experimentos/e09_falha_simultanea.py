from app import config
from cliente.resiliencia import chamar_com_failover
from experimentos.comum import Servidor, cabecalho_de, ident
from experimentos.proxy import ProxyDeFalhas

codigo = "E09"
titulo = "Falha simultânea de dois componentes"
hipotese = (
    "Com duas réplicas e failover no cliente, a queda de uma é mascarada: o cliente troca de réplica e só paga "
    "latência. Com as duas fora ao mesmo tempo, não há a quem recorrer e o retry só adia o erro. Com uma réplica "
    "lenta e a outra caída, o cliente termina com o erro da última tentativa e perde o diagnóstico da primeira."
)
falha_injetada = "réplica A encerrada; réplicas A e B encerradas; réplica A lenta (proxy com 1 s) e B encerrada"
classificacao = (
    "Combinação de falhas independentes: crash + crash e temporização + crash. A redundância tolera um crash; "
    "duas falhas simultâneas excedem a hipótese de falhas do projeto."
)

timeout = 0.5


def resumo(resultado, nomes):
    partes = []
    for item in resultado.tentativas:
        nome = next((rotulo for base, rotulo in nomes.items() if item.destino.startswith(base)), item.destino)
        partes.append(f"{nome}={item.categoria}")
    return " / ".join(partes)


def executar(coletor):
    banco = config.pasta_de_logs / "e09-compartilhado.db"
    replica_a = Servidor(ident(codigo, "replica-a"), banco=banco)
    replica_b = Servidor(ident(codigo, "replica-b"), banco=banco)
    replica_a.iniciar()
    replica_b.iniciar()
    try:
        enderecos = [replica_a.url, replica_b.url]
        nomes = {replica_a.url: "A", replica_b.url: "B"}
        livro = replica_a.cadastrar_livro("Grande Sertão: Veredas (E09)", exemplares=2)
        caminho = f"/v1/livros/{livro['id']}"

        normal = coletor.anotar(codigo, "A e B no ar", chamar_com_failover("GET", caminho, enderecos, timeout=timeout))
        coletor.registrar(
            codigo,
            "as duas réplicas no ar",
            "sucesso na 1a tentativa",
            f"{normal.categoria} na {len(normal.tentativas)}a tentativa",
            "Linha de base: a réplica A atende sozinha.",
        )

        replica_a.parar()
        uma = coletor.anotar(codigo, "A fora, B no ar", chamar_com_failover("GET", caminho, enderecos, timeout=timeout))
        coletor.registrar(
            codigo,
            "uma réplica fora",
            "sucesso na 2a tentativa",
            f"{uma.categoria} na {len(uma.tentativas)}a tentativa",
            f"O cliente pagou {uma.tentativas[0].duracao_ms:.0f} ms na réplica caída e foi atendido pela B. A falha "
            "foi mascarada; só a latência denuncia que algo aconteceu.",
        )
        emprestimo = coletor.anotar(
            codigo,
            "POST empréstimo com A fora",
            chamar_com_failover(
                "POST", f"{caminho}/emprestimos", enderecos, timeout=timeout,
                cabecalhos=cabecalho_de("atendente"), json={"leitor": "Diego Prado"},
            ),
        )
        coletor.registrar(
            codigo,
            "escrita durante a falha de uma réplica",
            201,
            emprestimo.status,
            "A escrita feita pela B vai para o mesmo banco que a A usava. O estado sobreviveu à queda porque não "
            "morava no processo, e é justamente por isso que o banco compartilhado é um ponto único de falha.",
        )

        replica_b.parar()
        duas = coletor.anotar(codigo, "A e B fora", chamar_com_failover("GET", caminho, enderecos, rodadas=2, timeout=timeout))
        coletor.registrar(
            codigo,
            "duas réplicas fora ao mesmo tempo",
            "falha após 4 tentativas",
            f"{'sucesso' if duas.ok else 'falha'} após {len(duas.tentativas)} tentativas",
            f"Duas rodadas de failover com backoff: {resumo(duas, nomes)}. O retry gastou "
            f"{duas.duracao_total_ms / 1000:.1f} s para chegar ao mesmo erro.",
            sucesso=not duas.ok and len(duas.tentativas) == 4,
        )

        replica_a.iniciar()
        with ProxyDeFalhas(replica_a.porta, modo="atraso", atraso=1.0) as proxy:
            nomes[proxy.url] = "A lenta"
            mista = coletor.anotar(
                codigo,
                "A lenta (proxy 1 s), B fora",
                chamar_com_failover("GET", caminho, [proxy.url, replica_b.url], rodadas=1, timeout=timeout),
            )
        coletor.registrar(
            codigo,
            "réplica lenta e réplica caída",
            "timeout-de-leitura, depois timeout-de-conexao",
            ", ".join(item.categoria for item in mista.tentativas),
            f"O erro final entregue ao chamador é '{mista.categoria}', da réplica B. A informação de que a A estava "
            "viva, mas lenta, só existe no registro por tentativa.",
            sucesso=[item.categoria for item in mista.tentativas] == ["timeout-de-leitura", "timeout-de-conexao"],
        )

        coletor.concluir(
            codigo,
            f"A e B no ar: {resumo(normal, nomes)}; A fora: {resumo(uma, nomes)}, empréstimo {emprestimo.status}; A e B fora: "
            f"{resumo(duas, nomes)} em {duas.duracao_total_ms / 1000:.1f} s; A lenta e B fora: {resumo(mista, nomes)}.",
            "A redundância mascarou um crash ao custo de latência, mas não duas falhas simultâneas. Com falhas de "
            "tipos diferentes, o erro final esconde a primeira causa: o diagnóstico depende do registro por "
            "tentativa. As réplicas compartilham o banco, então uma falha nele derrubaria as duas de uma vez "
            "(falha de modo comum).",
        )
    finally:
        replica_a.matar()
        replica_b.matar()
