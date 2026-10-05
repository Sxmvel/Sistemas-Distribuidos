import uuid

from cliente.resiliencia import chamar_com_retry, requisitar
from experimentos.comum import Servidor, cabecalho_de, ident

codigo = "E06"
titulo = "Retry em operação não idempotente"
hipotese = (
    "Se o servidor grava o empréstimo e demora 800 ms para responder, um cliente com timeout de 500 ms e retry "
    "registra um empréstimo novo a cada tentativa, embora veja só falhas. Com Idempotency-Key, as repetições "
    "devolvem o resultado da primeira execução e o domínio fica com um único empréstimo."
)
falha_injetada = "atraso de 800 ms depois da gravação do empréstimo (BIBLIOTECA_ATRASO_NA_ESCRITA=0.8)"
classificacao = (
    "Falha de temporização percebida pelo cliente que, somada a uma operação não idempotente e a retry cego, "
    "vira falha de resposta do sistema: transição de estado incorreta (empréstimo duplicado)."
)

timeout = 0.5
tentativas = 3


def executar(coletor):
    with Servidor(ident(codigo, "servidor"), atraso_na_escrita=0.8) as servidor:
        atendente = cabecalho_de("atendente")

        livro = servidor.cadastrar_livro("Vidas Secas (E06, sem chave)", exemplares=3)
        caminho = f"{servidor.url}/v1/livros/{livro['id']}/emprestimos"

        sem_chave = coletor.anotar(
            codigo,
            "POST empréstimo de Ana, sem chave, 3 tentativas",
            chamar_com_retry("POST", caminho, tentativas=tentativas, timeout=timeout, cabecalhos=atendente, json={"leitor": "Ana Ribeiro"}),
        )
        execucoes = servidor.esperar_eventos(sem_chave.correlacao, tentativas)
        coletor.registrar(
            codigo,
            "o que o cliente viu",
            f"{tentativas} timeouts",
            f"{sum(item.categoria == 'timeout-de-leitura' for item in sem_chave.tentativas)} timeouts",
            "Do ponto de vista do cliente, o empréstimo falhou três vezes.",
        )
        coletor.registrar(
            codigo,
            "o que o servidor fez",
            f"{tentativas} x 201",
            f"{sum(evento['status'] == 201 for evento in execucoes)} x 201",
            "Cada tentativa chegou, gravou e só então atrasou a resposta. O log mostra a mesma correlação com "
            "X-Tentativa 1, 2 e 3, todas com 201.",
        )
        ana = servidor.emprestimos_ativos(livro["id"], "Ana Ribeiro")
        coletor.registrar(
            codigo,
            "empréstimos ativos de Ana",
            tentativas,
            len(ana),
            "Uma intenção de negócio virou três empréstimos. O cliente acha que nada aconteceu; o acervo acha que "
            "Ana levou três exemplares do mesmo título.",
        )
        bruno = coletor.anotar(
            codigo,
            "POST empréstimo de Bruno (leitor legítimo)",
            requisitar("POST", caminho, timeout=2.0, cabecalhos=atendente, json={"leitor": "Bruno Tavares"}),
        )
        coletor.registrar(
            codigo,
            "outro leitor tenta emprestar o mesmo livro",
            409,
            bruno.status,
            "Efeito colateral visível para terceiros: os exemplares acabaram por causa dos retries.",
        )

        protegido = servidor.cadastrar_livro("Vidas Secas (E06, com chave)", exemplares=3)
        caminho = f"{servidor.url}/v1/livros/{protegido['id']}/emprestimos"
        chave = f"e06-{uuid.uuid4().hex}"
        com_chave_cabecalhos = {**atendente, "Idempotency-Key": chave}

        com_chave = coletor.anotar(
            codigo,
            "POST empréstimo de Ana, com chave, 3 tentativas",
            chamar_com_retry("POST", caminho, tentativas=tentativas, timeout=timeout, cabecalhos=com_chave_cabecalhos, json={"leitor": "Ana Ribeiro"}),
        )
        servidor.esperar_eventos(com_chave.correlacao, tentativas)
        coletor.registrar(
            codigo,
            "o que o cliente viu com chave",
            f"{tentativas} timeouts",
            f"{sum(item.categoria == 'timeout-de-leitura' for item in com_chave.tentativas)} timeouts",
            "A chave não acelera a resposta: o atraso continua e o cliente continua desistindo.",
        )
        ana_protegida = servidor.emprestimos_ativos(protegido["id"], "Ana Ribeiro")
        coletor.registrar(
            codigo,
            "empréstimos ativos de Ana com chave",
            1,
            len(ana_protegida),
            "As tentativas 2 e 3 encontraram a chave gravada na mesma transação do empréstimo e devolveram o "
            "resultado anterior em vez de repetir o efeito.",
        )

        confirmacao = coletor.anotar(
            codigo,
            "POST com a mesma chave e timeout 2 s",
            requisitar("POST", caminho, timeout=2.0, cabecalhos=com_chave_cabecalhos, json={"leitor": "Ana Ribeiro"}),
        )
        mesmo_id = confirmacao.ok and ana_protegida and confirmacao.resposta.json()["id"] == ana_protegida[0]["id"]
        coletor.registrar(
            codigo,
            "repetição com prazo suficiente devolve o mesmo empréstimo",
            "201, mesmo id, Idempotent-Replayed",
            f"{confirmacao.status}, {'mesmo id' if mesmo_id else 'id diferente'}, "
            f"{'Idempotent-Replayed' if confirmacao.ok and confirmacao.resposta.headers.get('Idempotent-Replayed') else 'sem marca'}",
            "O cliente finalmente recebe a resposta da execução que já tinha acontecido, marcada como repetição.",
        )

        outro = coletor.anotar(
            codigo,
            "mesma chave, outro leitor",
            requisitar("POST", caminho, timeout=2.0, cabecalhos=com_chave_cabecalhos, json={"leitor": "Carla Nunes"}),
        )
        coletor.registrar(
            codigo,
            "chave reutilizada em outro pedido",
            422,
            outro.status,
            "A chave guarda a impressão do pedido. Reaproveitá-la com outro conteúdo é erro do cliente e é recusado.",
        )

        coletor.concluir(
            codigo,
            f"sem chave: {tentativas} timeouts no cliente, {len(ana)} empréstimos de Ana gravados, Bruno recebeu "
            f"{bruno.status}; com chave: {tentativas} timeouts no cliente, {len(ana_protegida)} empréstimo gravado, "
            f"confirmação {confirmacao.status} com o mesmo id; chave em outro pedido: {outro.status}.",
            "Aqui o retry piorou o resultado: transformou uma falha de temporização em estado errado no domínio, com "
            "dano a um terceiro. O retry só é seguro em escrita quando a operação é idempotente por construção, "
            "como com a Idempotency-Key gravada na mesma transação do efeito.",
        )
