from app.erros import PrecondicaoFalhou

CABECALHO_ETAG = "ETag"
CABECALHO_CACHE = "Cache-Control"
POLITICA_DE_CACHE = "no-cache"


def gerar_etag(versao: int) -> str:
    return f'"{versao}"'


def separar_etags(cabecalho: str) -> set[str]:
    return {parte.strip().removeprefix("W/") for parte in cabecalho.split(",") if parte.strip()}


def representacao_inalterada(if_none_match: str | None, versao: int) -> bool:
    if not if_none_match:
        return False
    candidatos = separar_etags(if_none_match)
    return "*" in candidatos or gerar_etag(versao) in candidatos


def conferir_if_match(if_match: str | None, versao: int) -> None:
    if not if_match:
        return
    candidatos = separar_etags(if_match)
    if "*" in candidatos or gerar_etag(versao) in candidatos:
        return
    raise PrecondicaoFalhou(
        f"O recurso está na versão {versao} e o If-Match enviado não corresponde. "
        "Releia o recurso e reenvie a alteração."
    )
