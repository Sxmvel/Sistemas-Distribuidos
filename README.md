# Sistemas Distribuídos 🌐

Repositório dedicado aos projetos e atividades práticas da disciplina de Sistemas Distribuídos do 6º período do curso de Sistemas de Informação.

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python
* **Comunicação:** Sockets TCP/IP, HTTP/REST
* **Formatos de Dados:** CSV, JSON, XML, YAML, TOML
* **Frameworks:** FastAPI, Pydantic, pytest
* **Persistência:** SQLite (`sqlite3`)
* **Bibliotecas Externas:** `pyyaml`, `toml`, `requests`

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

### 📍 [Atividade Prática 2](Atividade-Pratica-2/README.MD)

#### API REST de gerenciamento de acervo de biblioteca
> Construção de uma API REST completa sobre HTTP, saindo do protocolo próprio da Atividade 1 para um protocolo de aplicação padronizado. O domínio escolhido é o acervo de uma biblioteca, com duas coleções relacionadas: **livros** e os **empréstimos** de cada livro.

A virada conceitual em relação à Atividade 1 está em perceber que problemas resolvidos manualmente lá já tinham solução no HTTP: o prefixo `FORMATO|payload` vira o cabeçalho `Content-Type`, e o ACK que evitava a junção de pacotes no TCP vira o `Content-Length`.

* **Recursos implementados:** 12 endpoints cobrindo `GET`, `POST`, `PUT`, `PATCH` e `DELETE`, com sub-recursos aninhados (`/v1/livros/{id}/emprestimos`).
* **Semântica HTTP:** uso deliberado de `200`, `201`, `204`, `304`, `404`, `409`, `412`, `422` e `503`, com `Location` na criação e `Retry-After` na indisponibilidade.
* **Validação:** modelos Pydantic separados para entrada e saída, com `extra="forbid"` rejeitando campos desconhecidos em vez de ignorá-los.
* **Tratamento de erros:** envelope único em `application/problem+json`, traduzindo erros técnicos do banco em erros de domínio sem vazar detalhes internos.
* **Concorrência:** controle otimista com `ETag`/`If-Match` (`412`) e validação condicional com `If-None-Match` (`304`), demonstrando a perda de atualização e o mecanismo que a impede.
* **Observabilidade:** log estruturado em JSON com identificador de correlação, método, caminho, status e duração de cada requisição.
* **Testes:** 45 testes automatizados em `pytest` e 8 cenários com cliente programático que geram a tabela de evidências automaticamente.
* **Principais aprendizados:** distinção entre recurso e representação; idempotência como propriedade do estado final e não da resposta; e a diferença crítica entre *"o servidor respondeu erro"* e *"o cliente não obteve resposta"* — a segunda deixa o cliente sem saber se a operação chegou a ser executada.

---
