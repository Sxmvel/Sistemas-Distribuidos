import socket
import threading
import time

modos = ("normal", "atraso", "perder-requisicao", "perder-resposta")


class ProxyDeFalhas:
    def __init__(self, porta_destino, modo="normal", atraso=0.0):
        self.porta_destino = porta_destino
        self.modo = modo
        self.atraso = atraso
        self.capturado = bytearray()
        self.conexoes_recebidas = 0
        self.trava = threading.Lock()
        self.tomadas = []
        self.ativo = False
        self.ouvinte = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ouvinte.bind(("127.0.0.1", 0))
        self.porta = self.ouvinte.getsockname()[1]

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}"

    def configurar(self, modo, atraso=0.0):
        if modo not in modos:
            raise ValueError(f"modo desconhecido: {modo}")
        self.modo = modo
        self.atraso = atraso

    def iniciar(self):
        self.ouvinte.listen(64)
        self.ativo = True
        threading.Thread(target=self.aceitar, daemon=True).start()
        return self

    def parar(self):
        self.ativo = False
        with self.trava:
            tomadas = [self.ouvinte, *self.tomadas]
        for tomada in tomadas:
            try:
                tomada.close()
            except OSError:
                pass

    def aceitar(self):
        while self.ativo:
            try:
                cliente, _ = self.ouvinte.accept()
            except OSError:
                return
            with self.trava:
                self.tomadas.append(cliente)
                self.conexoes_recebidas += 1
            threading.Thread(target=self.atender, args=(cliente, self.modo, self.atraso), daemon=True).start()

    def atender(self, cliente, modo, atraso):
        if modo == "perder-requisicao":
            self.encaminhar(cliente, None, "ida", modo, atraso)
            return
        try:
            servidor = socket.create_connection(("127.0.0.1", self.porta_destino), timeout=3)
            servidor.settimeout(None)
        except OSError:
            self.fechar(cliente)
            return
        with self.trava:
            self.tomadas.append(servidor)
        threading.Thread(
            target=self.encaminhar, args=(cliente, servidor, "ida", modo, atraso), daemon=True
        ).start()
        self.encaminhar(servidor, cliente, "volta", modo, atraso)

    def encaminhar(self, origem, destino, sentido, modo, atraso):
        atrasado = False
        try:
            while True:
                dados = origem.recv(65536)
                if not dados:
                    break
                if sentido == "ida":
                    with self.trava:
                        self.capturado.extend(dados)
                if destino is None:
                    continue
                if sentido == "volta" and modo == "perder-resposta":
                    continue
                if sentido == "volta" and modo == "atraso" and not atrasado:
                    time.sleep(atraso)
                    atrasado = True
                destino.sendall(dados)
        except OSError:
            pass
        finally:
            self.fechar(origem)
            if destino is not None:
                self.fechar(destino)

    def fechar(self, tomada):
        try:
            tomada.close()
        except OSError:
            pass

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *_):
        self.parar()
