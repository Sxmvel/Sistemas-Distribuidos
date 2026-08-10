import socket
import json
import csv
import io
import xml.etree.ElementTree as ET
import yaml
import toml

HOST = '127.0.0.1'  # Endereço localhost
PORT = 65432        # Porta de comunicação

def processar_mensagem(formato, payload):
    print(f"\n{'-'*40}")
    print(f"Recebido formato: {formato}")
    print(f"{'-'*40}")
    print(f"Texto Serializado:\n{payload}\n")
    
    dados = {}
    
    try:
        if formato == 'CSV':
            leitor = csv.reader(io.StringIO(payload))
            cabecalhos = next(leitor)
            valores = next(leitor)
            dados = dict(zip(cabecalhos, valores))
            
        elif formato == 'JSON':
            dados = json.loads(payload)
            
        elif formato == 'XML':
            raiz = ET.fromstring(payload)
            dados = {filho.tag: filho.text for filho in raiz}
            
        elif formato == 'YAML':
            dados = yaml.safe_load(payload)
            
        elif formato == 'TOML':
            dados = toml.loads(payload)
            
        print("Dados Manipulados (Dicionário Extraído):")
        print(f"  Nome:     {dados.get('nome')}")
        print(f"  CPF:      {dados.get('cpf')}")
        print(f"  Idade:    {dados.get('idade')}")
        print(f"  Mensagem: {dados.get('mensagem')}")

    except Exception as e:
        print(f"Erro ao processar o formato {formato}: {e}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor escutando em {HOST}:{PORT}...")
    
    conn, addr = s.accept()
    with conn:
        print(f"Cliente conectado: {addr}")
        
        while True:
            # Recebe a mensagem da rede
            dados_rede = conn.recv(4096).decode('utf-8')
            if not dados_rede:
                break
            
            # Separa o nome do formato do conteúdo real
            formato, payload = dados_rede.split('|', 1)
            
            # Processa e imprime
            processar_mensagem(formato, payload)
            
            # Envia uma confirmação ao cliente (ACK) para evitar aglomeração de pacotes no TCP
            conn.sendall(b"OK")