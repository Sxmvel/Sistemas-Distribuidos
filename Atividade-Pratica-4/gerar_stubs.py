import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

PACOTES = ("contratos", "contratos_legado", "contratos_incompativel")
GERADOS = ("*_pb2.py", "*_pb2_grpc.py", "*_pb2.pyi")

CABECALHO_DO_INIT = (
    "Stubs gerados por gerar_stubs.py a partir do arquivo .proto deste pacote.\n"
    "Nao edite os arquivos *_pb2*.py a mao.\n"
)


def limpar(pacote):
    pasta = RAIZ / pacote
    removidos = []
    for padrao in GERADOS:
        for arquivo in pasta.glob(padrao):
            arquivo.unlink()
            removidos.append(arquivo.name)
    cache = pasta / "__pycache__"
    if cache.exists():
        shutil.rmtree(cache)
    return removidos


def escrever_init(pacote):
    (RAIZ / pacote / "__init__.py").write_text(
        f'"""{CABECALHO_DO_INIT}"""\n', encoding="utf-8"
    )


def gerar(pacote, com_servico):
    proto = f"{pacote}/emprestimos.proto"
    comando = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        "-I.",
        "--python_out=.",
        "--pyi_out=.",
    ]
    if com_servico:
        comando.append("--grpc_python_out=.")
    comando.append(proto)

    processo = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True)
    if processo.returncode != 0:
        raise SystemExit(f"protoc falhou em {proto}:\n{processo.stderr.strip()}")
    return sorted(
        arquivo.name
        for padrao in GERADOS
        for arquivo in (RAIZ / pacote).glob(padrao)
    )


def main():
    for pacote in PACOTES:
        (RAIZ / pacote).mkdir(exist_ok=True)
        removidos = limpar(pacote)
        escrever_init(pacote)
        gerados = gerar(pacote, com_servico=pacote != "contratos_incompativel")
        print(f"{pacote}: removidos {len(removidos)} -> gerados {', '.join(gerados)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
