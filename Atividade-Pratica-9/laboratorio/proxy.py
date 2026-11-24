import asyncio
import threading

modos = ("repassar", "atrasar", "buraco_negro")


class ProxyDeFalhas:
    def __init__(self, porta, porta_destino, prazo_de_conexao_s=0.1):
        self.porta = porta
        self.porta_destino = porta_destino
        self.prazo_de_conexao_s = prazo_de_conexao_s
        self.modo = "repassar"
        self.atraso_s = 0.0
        self.conexoes = 0
        self.descartadas = 0
        self.laco = None
        self.servidor = None
        self.linha = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}"

    def configurar(self, modo, atraso_s=0.0):
        if modo not in modos:
            raise ValueError(f"modo desconhecido: {modo}")
        self.modo = modo
        self.atraso_s = atraso_s

    def iniciar(self):
        pronto = threading.Event()
        falha = []

        def rodar():
            self.laco = asyncio.new_event_loop()
            asyncio.set_event_loop(self.laco)
            try:
                self.servidor = self.laco.run_until_complete(asyncio.start_server(self.atender, "127.0.0.1", self.porta))
            except OSError as erro:
                falha.append(erro)
                pronto.set()
                return
            pronto.set()
            self.laco.run_forever()
            self.servidor.close()
            self.laco.run_until_complete(self.servidor.wait_closed())
            self.laco.close()

        self.linha = threading.Thread(target=rodar, daemon=True)
        self.linha.start()
        pronto.wait(5)
        if falha:
            raise falha[0]
        return self

    def parar(self):
        if self.laco is not None and self.laco.is_running():
            self.laco.call_soon_threadsafe(self.laco.stop)
            self.linha.join(5)

    async def atender(self, leitor, escritor):
        self.conexoes += 1
        try:
            leitor_destino, escritor_destino = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", self.porta_destino), self.prazo_de_conexao_s
            )
        except (OSError, asyncio.TimeoutError):
            if self.modo == "buraco_negro":
                await self.engolir(leitor)
            escritor.close()
            return
        await asyncio.gather(
            self.copiar(leitor, escritor_destino, ida=True),
            self.copiar(leitor_destino, escritor, ida=False),
        )

    async def engolir(self, leitor):
        try:
            while await leitor.read(65536):
                self.descartadas += 1
        except (ConnectionError, OSError):
            pass

    async def copiar(self, origem, destino, ida):
        try:
            while dados := await origem.read(65536):
                if ida and self.modo == "buraco_negro":
                    self.descartadas += 1
                    continue
                if not ida and self.modo == "atrasar":
                    await asyncio.sleep(self.atraso_s)
                destino.write(dados)
                await destino.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            destino.close()
