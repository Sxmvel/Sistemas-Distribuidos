import re
from dataclasses import dataclass
from datetime import date, timedelta

from app import config
from app.acervo import LIVROS, UNIDADES

ISBN_VALIDO = re.compile(r"^\d{13}$")
LEITOR_VALIDO = re.compile(r"^[a-z]{2,}\.[a-z]{2,}$")

CATALOGO = {livro["isbn"]: livro for livro in LIVROS}

ATIVO = "ativo"
DEVOLVIDO = "devolvido"


class ErroDeDominio(Exception):
    def __init__(self, categoria, mensagem, campo=None):
        super().__init__(mensagem)
        self.categoria = categoria
        self.mensagem = mensagem
        self.campo = campo


class EntradaInvalida(ErroDeDominio):
    def __init__(self, mensagem, campo=None):
        super().__init__("entrada_invalida", mensagem, campo)


class NaoEncontrado(ErroDeDominio):
    def __init__(self, mensagem, campo=None):
        super().__init__("nao_encontrado", mensagem, campo)


class PrecondicaoFalhou(ErroDeDominio):
    def __init__(self, mensagem, campo=None):
        super().__init__("precondicao_falhou", mensagem, campo)


class JaExiste(ErroDeDominio):
    def __init__(self, mensagem, campo=None):
        super().__init__("ja_existe", mensagem, campo)


@dataclass
class Emprestimo:
    codigo: str
    isbn: str
    titulo: str
    leitor: str
    unidade: str
    emprestado_em: date
    previsto_para: date
    devolvido_em: date = None

    @property
    def situacao(self):
        return DEVOLVIDO if self.devolvido_em else ATIVO

    def dias_de_atraso(self, referencia):
        fim = self.devolvido_em or referencia
        return max(0, (fim - self.previsto_para).days)

    def multa(self, referencia):
        return round(self.dias_de_atraso(referencia) * config.VALOR_DA_MULTA_POR_DIA, 2)


def validar_isbn(isbn):
    valor = (isbn or "").strip()
    if not valor:
        raise EntradaInvalida("isbn é obrigatório", "isbn")
    if not ISBN_VALIDO.match(valor):
        raise EntradaInvalida("isbn deve ter exatamente 13 dígitos", "isbn")
    return valor


def validar_leitor(leitor):
    valor = (leitor or "").strip().lower()
    if not valor:
        raise EntradaInvalida("leitor é obrigatório", "leitor")
    if not LEITOR_VALIDO.match(valor):
        raise EntradaInvalida("leitor deve seguir o formato nome.sobrenome", "leitor")
    return valor


def validar_dias(dias):
    if dias == 0:
        return config.PRAZO_EM_DIAS
    if dias < config.PRAZO_MINIMO_EM_DIAS or dias > config.PRAZO_MAXIMO_EM_DIAS:
        raise EntradaInvalida(
            f"dias deve estar entre {config.PRAZO_MINIMO_EM_DIAS} e "
            f"{config.PRAZO_MAXIMO_EM_DIAS}",
            "dias",
        )
    return dias


def validar_unidade(unidade):
    valor = (unidade or "").strip().lower()
    if not valor:
        return UNIDADES[0]
    if valor not in UNIDADES:
        raise EntradaInvalida(f"unidade deve ser uma de {', '.join(UNIDADES)}", "unidade")
    return valor


def validar_codigo(codigo):
    valor = (codigo or "").strip().upper()
    if not valor:
        raise EntradaInvalida("codigo é obrigatório", "codigo")
    return valor


def validar_data(texto, campo):
    valor = (texto or "").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise EntradaInvalida(f"{campo} deve estar no formato AAAA-MM-DD", campo)


def buscar_livro(isbn):
    livro = CATALOGO.get(isbn)
    if livro is None:
        raise NaoEncontrado(f"isbn {isbn} não está no acervo", "isbn")
    return livro


def prazo(inicio, dias):
    return inicio + timedelta(days=dias)
