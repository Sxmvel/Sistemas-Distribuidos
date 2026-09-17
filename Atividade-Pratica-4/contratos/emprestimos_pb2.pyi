from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Situacao(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SITUACAO_NAO_INFORMADA: _ClassVar[Situacao]
    SITUACAO_ATIVO: _ClassVar[Situacao]
    SITUACAO_DEVOLVIDO: _ClassVar[Situacao]
SITUACAO_NAO_INFORMADA: Situacao
SITUACAO_ATIVO: Situacao
SITUACAO_DEVOLVIDO: Situacao

class Emprestimo(_message.Message):
    __slots__ = ("codigo", "isbn", "titulo", "leitor", "emprestado_em", "previsto_para", "devolvido_em", "situacao", "unidade")
    CODIGO_FIELD_NUMBER: _ClassVar[int]
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITULO_FIELD_NUMBER: _ClassVar[int]
    LEITOR_FIELD_NUMBER: _ClassVar[int]
    EMPRESTADO_EM_FIELD_NUMBER: _ClassVar[int]
    PREVISTO_PARA_FIELD_NUMBER: _ClassVar[int]
    DEVOLVIDO_EM_FIELD_NUMBER: _ClassVar[int]
    SITUACAO_FIELD_NUMBER: _ClassVar[int]
    UNIDADE_FIELD_NUMBER: _ClassVar[int]
    codigo: str
    isbn: str
    titulo: str
    leitor: str
    emprestado_em: str
    previsto_para: str
    devolvido_em: str
    situacao: Situacao
    unidade: str
    def __init__(self, codigo: _Optional[str] = ..., isbn: _Optional[str] = ..., titulo: _Optional[str] = ..., leitor: _Optional[str] = ..., emprestado_em: _Optional[str] = ..., previsto_para: _Optional[str] = ..., devolvido_em: _Optional[str] = ..., situacao: _Optional[_Union[Situacao, str]] = ..., unidade: _Optional[str] = ...) -> None: ...

class RegistrarEmprestimoRequest(_message.Message):
    __slots__ = ("isbn", "leitor", "dias", "chave_idempotencia", "unidade")
    ISBN_FIELD_NUMBER: _ClassVar[int]
    LEITOR_FIELD_NUMBER: _ClassVar[int]
    DIAS_FIELD_NUMBER: _ClassVar[int]
    CHAVE_IDEMPOTENCIA_FIELD_NUMBER: _ClassVar[int]
    UNIDADE_FIELD_NUMBER: _ClassVar[int]
    isbn: str
    leitor: str
    dias: int
    chave_idempotencia: str
    unidade: str
    def __init__(self, isbn: _Optional[str] = ..., leitor: _Optional[str] = ..., dias: _Optional[int] = ..., chave_idempotencia: _Optional[str] = ..., unidade: _Optional[str] = ...) -> None: ...

class RegistrarEmprestimoResponse(_message.Message):
    __slots__ = ("emprestimo", "reaproveitado", "exemplares_disponiveis")
    EMPRESTIMO_FIELD_NUMBER: _ClassVar[int]
    REAPROVEITADO_FIELD_NUMBER: _ClassVar[int]
    EXEMPLARES_DISPONIVEIS_FIELD_NUMBER: _ClassVar[int]
    emprestimo: Emprestimo
    reaproveitado: bool
    exemplares_disponiveis: int
    def __init__(self, emprestimo: _Optional[_Union[Emprestimo, _Mapping]] = ..., reaproveitado: _Optional[bool] = ..., exemplares_disponiveis: _Optional[int] = ...) -> None: ...

class ConsultarEmprestimoRequest(_message.Message):
    __slots__ = ("codigo",)
    CODIGO_FIELD_NUMBER: _ClassVar[int]
    codigo: str
    def __init__(self, codigo: _Optional[str] = ...) -> None: ...

class ConsultarEmprestimoResponse(_message.Message):
    __slots__ = ("emprestimo",)
    EMPRESTIMO_FIELD_NUMBER: _ClassVar[int]
    emprestimo: Emprestimo
    def __init__(self, emprestimo: _Optional[_Union[Emprestimo, _Mapping]] = ...) -> None: ...

class RegistrarDevolucaoRequest(_message.Message):
    __slots__ = ("codigo", "devolvido_em")
    CODIGO_FIELD_NUMBER: _ClassVar[int]
    DEVOLVIDO_EM_FIELD_NUMBER: _ClassVar[int]
    codigo: str
    devolvido_em: str
    def __init__(self, codigo: _Optional[str] = ..., devolvido_em: _Optional[str] = ...) -> None: ...

class RegistrarDevolucaoResponse(_message.Message):
    __slots__ = ("emprestimo", "dias_de_atraso", "multa")
    EMPRESTIMO_FIELD_NUMBER: _ClassVar[int]
    DIAS_DE_ATRASO_FIELD_NUMBER: _ClassVar[int]
    MULTA_FIELD_NUMBER: _ClassVar[int]
    emprestimo: Emprestimo
    dias_de_atraso: int
    multa: float
    def __init__(self, emprestimo: _Optional[_Union[Emprestimo, _Mapping]] = ..., dias_de_atraso: _Optional[int] = ..., multa: _Optional[float] = ...) -> None: ...

class CalcularMultasRequest(_message.Message):
    __slots__ = ("codigos", "referencia")
    CODIGOS_FIELD_NUMBER: _ClassVar[int]
    REFERENCIA_FIELD_NUMBER: _ClassVar[int]
    codigos: _containers.RepeatedScalarFieldContainer[str]
    referencia: str
    def __init__(self, codigos: _Optional[_Iterable[str]] = ..., referencia: _Optional[str] = ...) -> None: ...

class MultaDoEmprestimo(_message.Message):
    __slots__ = ("codigo", "dias_de_atraso", "multa")
    CODIGO_FIELD_NUMBER: _ClassVar[int]
    DIAS_DE_ATRASO_FIELD_NUMBER: _ClassVar[int]
    MULTA_FIELD_NUMBER: _ClassVar[int]
    codigo: str
    dias_de_atraso: int
    multa: float
    def __init__(self, codigo: _Optional[str] = ..., dias_de_atraso: _Optional[int] = ..., multa: _Optional[float] = ...) -> None: ...

class CalcularMultasResponse(_message.Message):
    __slots__ = ("itens", "total", "quantidade")
    ITENS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    QUANTIDADE_FIELD_NUMBER: _ClassVar[int]
    itens: _containers.RepeatedCompositeFieldContainer[MultaDoEmprestimo]
    total: float
    quantidade: int
    def __init__(self, itens: _Optional[_Iterable[_Union[MultaDoEmprestimo, _Mapping]]] = ..., total: _Optional[float] = ..., quantidade: _Optional[int] = ...) -> None: ...

class ListarEmprestimosRequest(_message.Message):
    __slots__ = ("leitor", "situacao", "limite")
    LEITOR_FIELD_NUMBER: _ClassVar[int]
    SITUACAO_FIELD_NUMBER: _ClassVar[int]
    LIMITE_FIELD_NUMBER: _ClassVar[int]
    leitor: str
    situacao: Situacao
    limite: int
    def __init__(self, leitor: _Optional[str] = ..., situacao: _Optional[_Union[Situacao, str]] = ..., limite: _Optional[int] = ...) -> None: ...
