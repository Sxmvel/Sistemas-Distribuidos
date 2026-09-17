from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
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
    __slots__ = ("codigo", "isbn", "titulo", "unidade", "emprestado_em", "previsto_para", "devolvido_em", "situacao")
    CODIGO_FIELD_NUMBER: _ClassVar[int]
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITULO_FIELD_NUMBER: _ClassVar[int]
    UNIDADE_FIELD_NUMBER: _ClassVar[int]
    EMPRESTADO_EM_FIELD_NUMBER: _ClassVar[int]
    PREVISTO_PARA_FIELD_NUMBER: _ClassVar[int]
    DEVOLVIDO_EM_FIELD_NUMBER: _ClassVar[int]
    SITUACAO_FIELD_NUMBER: _ClassVar[int]
    codigo: str
    isbn: str
    titulo: str
    unidade: str
    emprestado_em: str
    previsto_para: str
    devolvido_em: str
    situacao: Situacao
    def __init__(self, codigo: _Optional[str] = ..., isbn: _Optional[str] = ..., titulo: _Optional[str] = ..., unidade: _Optional[str] = ..., emprestado_em: _Optional[str] = ..., previsto_para: _Optional[str] = ..., devolvido_em: _Optional[str] = ..., situacao: _Optional[_Union[Situacao, str]] = ...) -> None: ...

class RegistrarEmprestimoRequest(_message.Message):
    __slots__ = ("isbn", "leitor", "dias", "chave_idempotencia", "unidade")
    ISBN_FIELD_NUMBER: _ClassVar[int]
    LEITOR_FIELD_NUMBER: _ClassVar[int]
    DIAS_FIELD_NUMBER: _ClassVar[int]
    CHAVE_IDEMPOTENCIA_FIELD_NUMBER: _ClassVar[int]
    UNIDADE_FIELD_NUMBER: _ClassVar[int]
    isbn: str
    leitor: str
    dias: str
    chave_idempotencia: str
    unidade: str
    def __init__(self, isbn: _Optional[str] = ..., leitor: _Optional[str] = ..., dias: _Optional[str] = ..., chave_idempotencia: _Optional[str] = ..., unidade: _Optional[str] = ...) -> None: ...
