import socket
import json
import csv
import io
import xml.etree.ElementTree as ET
import yaml
import toml

HOST = '127.0.0.1'
PORT = 65432

# Informações base exigidas
info_cliente = {
    "nome": "Fulano",
    "cpf": "10326709722",
    "idade": 45,
    "mensagem": "segue comprovante de endereço"
}

# 1. Preparar CSV
saida_csv = io.StringIO()
escritor = csv.DictWriter(saida_csv, fieldnames=info_cliente.keys())
escritor.writeheader()
escritor.writerow(info_cliente)
payload_csv = saida_csv.getvalue().strip()

# 2. Preparar JSON
payload_json = json.dumps(info_cliente)

# 3. Preparar XML
raiz_xml = ET.Element("cliente")
for chave, valor in info_cliente.items():
    filho = ET.SubElement(raiz_xml, chave)
    filho.text = str(valor)
payload_xml = ET.tostring(raiz_xml, encoding='unicode')

# 4. Preparar YAML
payload_yaml = yaml.dump(info_cliente, default_flow_style=False).strip()

# 5. Preparar TOML
payload_toml = toml.dumps(info_cliente).strip()

mensagens = [
    ("CSV", payload_csv),
    ("JSON", payload_json),
    ("XML", payload_xml),
    ("YAML", payload_yaml),
    ("TOML", payload_toml)
]

# Configuração do Socket Cliente
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    
    for formato, payload in mensagens:
        mensagem_final = f"{formato}|{payload}"
        
        print(f"Enviando mensagem formatada em {formato}...")
        s.sendall(mensagem_final.encode('utf-8'))
        
        resposta = s.recv(1024)
        print(f"Status do servidor: {resposta.decode('utf-8')}\n")