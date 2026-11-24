import json
import platform
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime

from laboratorio.processos import Servico, pasta_de_logs, raiz
from laboratorio.proxy import ProxyDeFalhas
from medicao.traces import ler_eventos
from servicos.relogio import ativar_relogio_fino

sys.stdout.reconfigure(encoding="utf-8")
relogio_fino = ativar_relogio_fino()
pasta_de_entrega = raiz / "entregavel"
pasta_de_evidencias = pasta_de_entrega / "evidencias"
portas_do_acervo = (8201, 8202)
portas_dos_proxies = (8301, 8302)
porta_do_balcao = 8100
nomes_das_replicas = ("acervo-a", "acervo-b")


def num(valor, casas=1):
    if valor is None:
        return "-"
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(valor, casas=1):
    if valor is None:
        return "-"
    return f"{num(valor * 100, casas)}%"


def ambiente_de_execucao():
    return {
        "python": sys.version.split()[0],
        "sistema": f"{platform.system()} {platform.release()}",
        "processador": platform.processor() or platform.machine(),
        "relogio_fino": relogio_fino,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


class Laboratorio:
    def __init__(self, experimento, replicas=2, acervo=None, por_replica=None, balcao=None, proxies=False):
        self.pasta = pasta_de_logs / experimento
        self.quantidade = replicas
        self.acervo = acervo or {}
        self.por_replica = por_replica or [{} for _ in range(replicas)]
        self.balcao_ambiente = balcao or {}
        self.usar_proxies = proxies
        self.replicas = []
        self.proxies = []
        self.balcao = None

    def __enter__(self):
        shutil.rmtree(self.pasta, ignore_errors=True)
        self.pasta.mkdir(parents=True, exist_ok=True)
        try:
            for indice in range(self.quantidade):
                nome = nomes_das_replicas[indice]
                ambiente = {"ACERVO_INSTANCIA": nome, **self.acervo, **self.por_replica[indice]}
                self.replicas.append(Servico(nome, "servicos.acervo:criar_app", portas_do_acervo[indice], ambiente, self.pasta).iniciar())
            destinos = [r.url for r in self.replicas]
            if self.usar_proxies:
                for indice, replica in enumerate(self.replicas):
                    self.proxies.append(ProxyDeFalhas(portas_dos_proxies[indice], replica.porta).iniciar())
                destinos = [p.url for p in self.proxies]
            ambiente = {"BALCAO_INSTANCIA": "balcao-1", "BALCAO_REPLICAS": ",".join(destinos), **self.balcao_ambiente}
            self.balcao = Servico("balcao", "servicos.balcao:criar_app", porta_do_balcao, ambiente, self.pasta).iniciar()
        except BaseException:
            self.encerrar()
            raise
        return self

    def __exit__(self, *_):
        self.encerrar()

    def encerrar(self):
        if self.balcao:
            self.balcao.matar()
        for proxy in self.proxies:
            proxy.parar()
        for replica in self.replicas:
            replica.matar()

    def url(self, caminho):
        return self.balcao.url + caminho

    def eventos(self):
        return ler_eventos(*(s.log for s in [self.balcao, *self.replicas]))


@dataclass
class Verificacao:
    descricao: str
    esperado: str
    obtido: str
    sucesso: bool


@dataclass
class Relato:
    codigo: str
    titulo: str
    pergunta: str
    secoes_do_material: str
    hipotese: str = ""
    procedimento: list = field(default_factory=list)
    blocos: list = field(default_factory=list)
    verificacoes: list = field(default_factory=list)
    conclusao: str = ""
    dados: dict = field(default_factory=dict)
    ambiente: dict = field(default_factory=ambiente_de_execucao)

    def tabela(self, titulo, cabecalho, linhas, nota=""):
        self.blocos.append({"tipo": "tabela", "titulo": titulo, "cabecalho": cabecalho, "linhas": linhas, "nota": nota})
        print(f"\n  {titulo}")
        print("  " + " | ".join(cabecalho))
        for linha in linhas:
            print("  " + " | ".join(str(c) for c in linha))

    def texto(self, titulo, conteudo, codigo=False):
        self.blocos.append({"tipo": "codigo" if codigo else "texto", "titulo": titulo, "conteudo": conteudo})
        print(f"\n  {titulo}\n" + "\n".join("    " + l for l in conteudo.splitlines()))

    def verificar(self, descricao, esperado, obtido, sucesso):
        self.verificacoes.append(Verificacao(descricao, str(esperado), str(obtido), bool(sucesso)))
        marca = "OK   " if sucesso else "FALHA"
        print(f"  [{marca}] {descricao:<64} esperado={esperado} obtido={obtido}")
        return sucesso

    def veredito(self):
        if all(v.sucesso for v in self.verificacoes):
            return "Hipótese confirmada."
        return "Hipótese só parcialmente confirmada: ver as verificações que falharam."

    def salvar(self):
        pasta_de_evidencias.mkdir(parents=True, exist_ok=True)
        destino = pasta_de_evidencias / f"{self.codigo.lower()}.json"
        conteudo = asdict(self)
        destino.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        aprovadas = sum(1 for v in self.verificacoes if v.sucesso)
        print(f"\n  {self.codigo}: {aprovadas}/{len(self.verificacoes)} verificações; evidência em {destino.relative_to(raiz)}")
        return destino


def linha_de_resumo(rotulo, resumo, extras=()):
    return [
        rotulo,
        resumo["n"],
        num(resumo["media_ms"]),
        num(resumo["p50_ms"]),
        num(resumo["p95_ms"]),
        num(resumo["p99_ms"]),
        num(resumo["max_ms"]),
        num(resumo["vazao_rps"]),
        *extras,
    ]


cabecalho_de_resumo = ["cenário", "n", "média (ms)", "p50 (ms)", "p95 (ms)", "p99 (ms)", "máx (ms)", "vazão (req/s)"]
