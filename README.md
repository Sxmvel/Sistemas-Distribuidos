# Sistemas Distribuídos 🌐

Repositório dedicado aos projetos e atividades práticas da disciplina de Sistemas Distribuídos do 6º período do curso de Sistemas de Informação.

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python
* **Comunicação:** Sockets TCP/IP
* **Formatos de Dados:** CSV, JSON, XML, YAML, TOML
* **Bibliotecas Externas:** `pyyaml`, `toml`

---

## 🚀 Atividades Realizadas

### 📍 Atividade Prática 1

#### Atividade 1.1: Demonstração de Formatos de Serialização Baseados em Texto
> Esta atividade consiste em um estudo comparativo prático sobre como diferentes linguagens estruturam e serializam a mesma informação em texto puro. Utilizando um conjunto de dados padronizado, a atividade demonstra as diferenças de sintaxe, aninhamento de estruturas complexas (como listas) e legibilidade humana.

* **Formatos analisados:** `CSV`, `JSON`, `XML`, `YAML` e `TOML`.
* **Principais aprendizados:** Compreensão das características estruturais de cada formato, identificando suas vantagens, limitações e aplicações mais comuns no mercado (como o uso de JSON em APIs modernas, XML em sistemas legados/fiscais e YAML/TOML em arquivos de configuração e DevOps).

#### Atividade 1.2: Cliente-Servidor com Serialização de Dados
Desenvolvimento de um sistema de troca de mensagens em rede demonstrando o uso de diferentes formatos de serialização baseados em texto.

O **Cliente** empacota um conjunto de dados predefinidos (Nome, CPF, Idade, Mensagem) e os transmite sequencialmente. O **Servidor** intercepta a comunicação, identifica qual formato foi utilizado, realiza a desserialização e imprime os dados processados em tela.

* **Formatos implementados e validados:**
  1. `CSV` (Comma-Separated Values)
  2. `JSON` (JavaScript Object Notation)
  3. `XML` (eXtensible Markup Language)
  4. `YAML` (YAML Ain't Markup Language)
  5. `TOML` (Tom's Obvious, Minimal Language)
* **Controle de Fluxo:** Implementação de uma confirmação simples de recebimento (ACK) para evitar a junção de pacotes no buffer do protocolo TCP.

---
