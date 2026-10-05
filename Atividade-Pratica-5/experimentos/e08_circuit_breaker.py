import time

from cliente.resiliencia import Disjuntor, requisitar
from experimentos.comum import Servidor, ident

codigo = "E08"
titulo = "Circuit breaker diante de dependência fora do ar"
hipotese = (
    "Com a dependência fora do ar, sem disjuntor toda chamada paga o timeout na rede. Um disjuntor que abre após "
    "3 falhas seguidas faz as chamadas seguintes falharem na hora, sem tocar a rede, e fecha sozinho quando a "
    "chamada de teste (meio-aberto) tem sucesso."
)
falha_injetada = "servidor encerrado durante 12 chamadas; religado em seguida"
classificacao = (
    "Crash da dependência, tratado no chamador. O disjuntor não corrige a falha: troca espera na rede por falha "
    "local imediata e alivia a dependência enquanto ela se recupera."
)

chamadas = 12
timeout = 0.5


def executar(coletor):
    servidor = Servidor(ident(codigo, "servidor"))
    servidor.iniciar()
    try:
        destino = f"{servidor.url}/v1/saude"
        servidor.parar()

        sem_disjuntor = [
            coletor.anotar(codigo, "sem disjuntor", requisitar("GET", destino, timeout=timeout), detalhar=False)
            for _ in range(chamadas)
        ]
        custo_sem = sum(resultado.ultima.duracao_ms for resultado in sem_disjuntor)

        disjuntor = Disjuntor(limite_de_falhas=3, tempo_aberto=1.5)
        com_disjuntor = [
            coletor.anotar(codigo, "com disjuntor", disjuntor.chamar("GET", destino, timeout=timeout))
            for _ in range(chamadas)
        ]
        custo_com = sum(resultado.ultima.duracao_ms for resultado in com_disjuntor)
        na_rede = [resultado for resultado in com_disjuntor if resultado.categoria != "circuito-aberto"]
        rejeitadas = [resultado for resultado in com_disjuntor if resultado.categoria == "circuito-aberto"]

        coletor.registrar(
            codigo,
            "tentativas que chegaram à rede sem disjuntor",
            chamadas,
            len(sem_disjuntor),
            f"Cada chamada esperou o timeout de conexão: {custo_sem:.0f} ms somados.",
        )
        coletor.registrar(
            codigo,
            "tentativas que chegaram à rede com disjuntor",
            3,
            len(na_rede),
            f"Depois de 3 falhas seguidas o circuito abriu e as outras {len(rejeitadas)} chamadas falharam "
            f"localmente. Custo total: {custo_com:.0f} ms.",
        )
        coletor.registrar(
            codigo,
            "latência de uma chamada rejeitada pelo circuito aberto",
            "< 1 ms",
            f"{max((resultado.ultima.duracao_ms for resultado in rejeitadas), default=0):.1f} ms",
            "Falha rápida: o chamador libera a thread na hora em vez de segurá-la por 500 ms.",
            sucesso=bool(rejeitadas) and all(resultado.ultima.duracao_ms < 1 for resultado in rejeitadas),
        )

        time.sleep(disjuntor.tempo_aberto)
        teste_com_falha = coletor.anotar(codigo, "teste meio-aberto, servidor ainda fora", disjuntor.chamar("GET", destino, timeout=timeout))
        coletor.registrar(
            codigo,
            "teste no meio-aberto com a dependência ainda fora",
            "aberto",
            disjuntor.estado,
            f"Uma única chamada de teste ({teste_com_falha.categoria}) e o circuito reabre: não houve rajada de "
            "tentativas contra a dependência ainda caída.",
        )

        servidor.iniciar()
        time.sleep(disjuntor.tempo_aberto)
        recuperada = coletor.anotar(codigo, "teste meio-aberto, servidor de volta", disjuntor.chamar("GET", destino, timeout=timeout))
        coletor.registrar(
            codigo,
            "teste no meio-aberto com a dependência de volta",
            "sucesso / fechado",
            f"{recuperada.categoria} / {disjuntor.estado}",
            "A chamada de teste passou e o circuito voltou ao normal sem intervenção manual.",
        )

        transicoes = " -> ".join([disjuntor.historico[0][0], *[estado for _, estado in disjuntor.historico]])
        coletor.registrar(
            codigo,
            "sequência de estados do disjuntor",
            "fechado -> aberto -> meio-aberto -> aberto -> meio-aberto -> fechado",
            transicoes,
            "O ciclo completo de estados do padrão, registrado pelo próprio disjuntor.",
        )

        coletor.concluir(
            codigo,
            f"sem disjuntor: {chamadas} tentativas na rede, {custo_sem:.0f} ms somados; com disjuntor: {len(na_rede)} "
            f"na rede, {len(rejeitadas)} rejeitadas localmente, {custo_com:.0f} ms somados; estados: {transicoes}.",
            f"O disjuntor reduziu o tempo gasto esperando a dependência de {custo_sem:.0f} para {custo_com:.0f} ms e "
            "limitou a pressão sobre ela durante a recuperação. O risco é a política: tempo aberto longo demais "
            "atrasa a volta; curto demais vira retry disfarçado.",
        )
    finally:
        servidor.matar()
