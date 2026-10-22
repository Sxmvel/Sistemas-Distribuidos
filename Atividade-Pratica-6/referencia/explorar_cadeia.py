from dataclasses import dataclass, asdict
import hashlib, json


@dataclass
class Bloco:
    indice: int
    dados: str
    hash_anterior: str
    hash: str = ""

    def calcular_hash(self):
        base = {"indice": self.indice, "dados": self.dados, "hash_anterior": self.hash_anterior}
        raw = json.dumps(base, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()


def novo(indice, dados, anterior):
    b = Bloco(indice, dados, anterior)
    b.hash = b.calcular_hash()
    return b


cadeia = [novo(0, "genesis", "0" * 64)]
for dado in ["A->B:10", "B->C:3", "C->D:1"]:
    cadeia.append(novo(len(cadeia), dado, cadeia[-1].hash))


def validar(cadeia):
    for i, b in enumerate(cadeia):
        if b.hash != b.calcular_hash():
            return False, f"hash inválido no bloco {i}"
        if i > 0 and b.hash_anterior != cadeia[i-1].hash:
            return False, f"ligação inválida no bloco {i}"
    return True, "cadeia válida"


print(validar(cadeia))
cadeia[1].dados = "A->B:1000"
print(validar(cadeia))
