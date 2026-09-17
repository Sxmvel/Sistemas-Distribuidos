import itertools
import threading
from datetime import date

from app import dominio
from app.dominio import (
    Emprestimo,
    JaExiste,
    NaoEncontrado,
    PrecondicaoFalhou,
)


def impressao_do_pedido(isbn, leitor, dias, unidade):
    return f"{isbn}|{leitor}|{dias}|{unidade}"


class Repositorio:
    def __init__(self):
        self._trava = threading.RLock()
        self._emprestimos = {}
        self._por_chave = {}
        self._contador = itertools.count(1)
        self.conflitos_de_exemplar = 0

    def _proximo_codigo(self):
        return f"EMP-{next(self._contador):04d}"

    def _ativos_do_isbn(self, isbn):
        return sum(
            1
            for item in self._emprestimos.values()
            if item.isbn == isbn and item.situacao == dominio.ATIVO
        )

    def disponiveis(self, isbn):
        livro = dominio.buscar_livro(isbn)
        with self._trava:
            return livro["exemplares"] - self._ativos_do_isbn(isbn)

    def registrar(self, isbn, leitor, dias, unidade, chave, hoje=None):
        livro = dominio.buscar_livro(isbn)
        hoje = hoje or date.today()
        impressao = impressao_do_pedido(isbn, leitor, dias, unidade)

        with self._trava:
            if chave:
                anterior = self._por_chave.get(chave)
                if anterior is not None:
                    if anterior["impressao"] != impressao:
                        raise JaExiste(
                            f"chave de idempotência {chave} já foi usada com outro pedido",
                            "chave_idempotencia",
                        )
                    emprestimo = self._emprestimos[anterior["codigo"]]
                    return emprestimo, True, self._disponiveis_sem_trava(livro)

            if self._disponiveis_sem_trava(livro) <= 0:
                self.conflitos_de_exemplar += 1
                raise PrecondicaoFalhou(
                    f"não há exemplar disponível de {livro['titulo']}", "isbn"
                )

            codigo = self._proximo_codigo()
            emprestimo = Emprestimo(
                codigo=codigo,
                isbn=isbn,
                titulo=livro["titulo"],
                leitor=leitor,
                unidade=unidade,
                emprestado_em=hoje,
                previsto_para=dominio.prazo(hoje, dias),
            )
            self._emprestimos[codigo] = emprestimo
            if chave:
                self._por_chave[chave] = {"impressao": impressao, "codigo": codigo}
            return emprestimo, False, self._disponiveis_sem_trava(livro)

    def _disponiveis_sem_trava(self, livro):
        return livro["exemplares"] - self._ativos_do_isbn(livro["isbn"])

    def consultar(self, codigo):
        with self._trava:
            emprestimo = self._emprestimos.get(codigo)
        if emprestimo is None:
            raise NaoEncontrado(f"empréstimo {codigo} não existe", "codigo")
        return emprestimo

    def devolver(self, codigo, devolvido_em=None):
        devolvido_em = devolvido_em or date.today()
        with self._trava:
            emprestimo = self.consultar(codigo)
            if emprestimo.situacao == dominio.DEVOLVIDO:
                raise PrecondicaoFalhou(
                    f"empréstimo {codigo} já foi devolvido em {emprestimo.devolvido_em}",
                    "codigo",
                )
            if devolvido_em < emprestimo.emprestado_em:
                raise PrecondicaoFalhou(
                    "devolução anterior à data do empréstimo", "devolvido_em"
                )
            emprestimo.devolvido_em = devolvido_em
            return emprestimo

    def listar(self, leitor=None, situacao=None, limite=None):
        with self._trava:
            itens = list(self._emprestimos.values())
        if leitor:
            itens = [item for item in itens if item.leitor == leitor]
        if situacao:
            itens = [item for item in itens if item.situacao == situacao]
        itens.sort(key=lambda item: item.codigo)
        if limite:
            itens = itens[:limite]
        return itens

    @property
    def total(self):
        with self._trava:
            return len(self._emprestimos)

    def semear(self, quantidade=4, hoje=None):
        hoje = hoje or date.today()
        from app.acervo import LEITORES

        criados = []
        for indice in range(quantidade):
            livro = dominio.LIVROS[indice % len(dominio.LIVROS)]
            leitor = LEITORES[indice % len(LEITORES)]
            emprestimo, _, _ = self.registrar(
                livro["isbn"],
                leitor,
                7,
                "central",
                chave=f"semente-{indice}",
                hoje=hoje,
            )
            criados.append(emprestimo)
        return criados
