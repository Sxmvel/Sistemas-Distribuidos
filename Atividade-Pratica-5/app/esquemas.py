from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CARACTERES_DE_ISBN = set("0123456789-X")


def normalizar_isbn(valor: str) -> str:
    normalizado = valor.strip().upper()
    if not set(normalizado) <= CARACTERES_DE_ISBN:
        raise ValueError("o isbn aceita apenas dígitos, hífen e a letra X")
    if sum(caractere.isdigit() for caractere in normalizado) < 10:
        raise ValueError("o isbn precisa conter ao menos 10 dígitos")
    return normalizado


class LivroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=2, max_length=200)
    autor: str = Field(min_length=2, max_length=120)
    isbn: str = Field(min_length=10, max_length=20)
    ano: int = Field(ge=1450, le=2100)
    exemplares_total: int = Field(ge=1, le=1000)

    @field_validator("titulo", "autor", "isbn")
    @classmethod
    def remover_espacos_das_pontas(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("isbn")
    @classmethod
    def validar_formato_do_isbn(cls, valor: str) -> str:
        return normalizar_isbn(valor)


class LivroParcial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    autor: str | None = Field(default=None, min_length=2, max_length=120)
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    ano: int | None = Field(default=None, ge=1450, le=2100)
    exemplares_total: int | None = Field(default=None, ge=1, le=1000)

    @field_validator("isbn")
    @classmethod
    def validar_formato_do_isbn(cls, valor: str | None) -> str | None:
        return None if valor is None else normalizar_isbn(valor)

    @model_validator(mode="after")
    def exigir_ao_menos_um_campo(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("informe ao menos um campo para atualizar")
        return self


class Livro(BaseModel):
    id: int
    titulo: str
    autor: str
    isbn: str
    ano: int
    exemplares_total: int
    exemplares_disponiveis: int
    versao: int


class PaginaDeLivros(BaseModel):
    itens: list[Livro]
    pagina: int
    tamanho: int
    total: int
    total_de_paginas: int


class EmprestimoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leitor: str = Field(min_length=2, max_length=120)

    @field_validator("leitor")
    @classmethod
    def remover_espacos_das_pontas(cls, valor: str) -> str:
        return valor.strip()


class EmprestimoParcial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    devolvido: Literal[True]


class Emprestimo(BaseModel):
    id: int
    livro_id: int
    leitor: str
    emprestado_em: str
    devolvido_em: str | None = None
