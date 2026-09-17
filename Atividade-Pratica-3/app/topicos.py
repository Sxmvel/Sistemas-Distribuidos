RAIZ = "biblioteca"

EMPRESTIMO = "emprestimo"
DEVOLUCAO = "devolucao"
STATUS = "status"

EVENTOS = (EMPRESTIMO, DEVOLUCAO, STATUS)
MOVIMENTACOES = (EMPRESTIMO, DEVOLUCAO)
NIVEIS = ("raiz", "unidade", "terminal", "evento")

FILTRO_DE_EMPRESTIMOS = f"{RAIZ}/+/+/{EMPRESTIMO}"
FILTRO_DE_DEVOLUCOES = f"{RAIZ}/+/+/{DEVOLUCAO}"
FILTRO_DE_STATUS = f"{RAIZ}/+/+/{STATUS}"
FILTRO_DE_TUDO = f"{RAIZ}/#"


class TopicoInvalido(Exception):
    pass


def _validar_nivel(valor, nome):
    if not valor:
        raise TopicoInvalido(f"{nome} não pode ser vazio")
    if any(caractere in valor for caractere in ("/", "+", "#")):
        raise TopicoInvalido(f"{nome} não pode conter '/', '+' ou '#': {valor!r}")
    return valor


def montar(unidade, terminal, evento):
    _validar_nivel(unidade, "unidade")
    _validar_nivel(terminal, "terminal")
    if evento not in EVENTOS:
        raise TopicoInvalido(f"evento desconhecido: {evento!r}")
    return f"{RAIZ}/{unidade}/{terminal}/{evento}"


def de_status(unidade, terminal):
    return montar(unidade, terminal, STATUS)


def decompor(topico):
    partes = topico.split("/")
    if len(partes) != 4 or partes[0] != RAIZ:
        raise TopicoInvalido(f"tópico fora da taxonomia: {topico!r}")
    return dict(zip(NIVEIS, partes))


def unidade_de(topico):
    return decompor(topico)["unidade"]


def terminal_de(topico):
    return decompor(topico)["terminal"]


def evento_de(topico):
    return decompor(topico)["evento"]


def casa_com(filtro, topico):
    niveis_do_filtro = filtro.split("/")
    niveis_do_topico = topico.split("/")
    for indice, nivel in enumerate(niveis_do_filtro):
        if nivel == "#":
            return indice <= len(niveis_do_topico)
        if indice >= len(niveis_do_topico):
            return False
        if nivel != "+" and nivel != niveis_do_topico[indice]:
            return False
    return len(niveis_do_filtro) == len(niveis_do_topico)
