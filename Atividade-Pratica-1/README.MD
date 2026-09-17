# AP1 — Serialização em texto e comunicação com sockets TCP

Primeira atividade prática de Sistemas Distribuídos. Ela responde à pergunta mais básica da
disciplina: **como dois processos separados trocam dados estruturados?**

A resposta tem duas partes, e a atividade é dividida nelas:

| Parte | Pergunta | Onde |
| --- | --- | --- |
| **1.1** | Como representar dados estruturados em texto? | arquivos na raiz desta pasta |
| **1.2** | Como fazer esse texto atravessar a rede? | [`Atividade-1.2/`](Atividade-1.2/) |

Não há framework, biblioteca de rede nem protocolo de aplicação pronto. Tudo é construído
com `socket` e com as bibliotecas de serialização — e é justamente essa ausência que faz a
atividade valer: ela mostra, na prática, quais problemas um protocolo padronizado resolve, o
que prepara o terreno para o HTTP da [AP2](../Atividade-Pratica-2/README.MD).

---

## Parte 1.1 — Formatos de serialização baseados em texto

### O que a parte 1.1 investiga

Serializar é converter uma estrutura de memória em uma sequência de caracteres que possa ser
gravada ou transmitida. Cada formato faz escolhas diferentes sobre o que priorizar: tamanho,
legibilidade humana, capacidade de representar aninhamento ou fidelidade de tipos.

Para que a comparação seja honesta, **o mesmo conjunto de dados** foi escrito nos cinco
formatos. O conjunto foi escolhido para exercitar os pontos onde eles divergem:

* uma **coleção** — dois registros, não um;
* tipos **diferentes** — inteiro (`idade`), texto (`nome`), booleano (`matriculado`);
* uma **lista aninhada** — `habilidades`, que é onde o CSV quebra.

Os registros são idênticos nos cinco arquivos. O que muda é o nome do nó raiz, e a variação é
em si informativa: XML e TOML nomeiam a coleção (`<Alunos>`, `[[Alunos]]`), JSON dispensa o
nome e começa direto no array, o YAML usa `funcionarios:`, e o CSV não tem onde colocar um nome
de coleção — o arquivo *é* a coleção.

### Os cinco arquivos

| Arquivo | Formato | Como representa a coleção | Como representa a lista aninhada |
| --- | --- | --- | --- |
| [`csv.csv`](csv.csv) | CSV | uma linha por registro | **não representa** — precisa colapsar em `"Python, SQL"` dentro de uma célula |
| [`json.json`](json.json) | JSON | array de objetos | array nativo `["Python", "SQL"]` |
| [`xml.xml`](xml.xml) | XML | elementos `<Aluno>` repetidos | elemento `<habilidades>` com filhos `<habilidade>` |
| [`yaml.yaml`](yaml.yaml) | YAML | sequência com `-` | sequência indentada |
| [`toml.toml`](toml.toml) | TOML | tabelas de array `[[Alunos]]` | array inline `["Python", "SQL"]` |

### O que cada formato revela

**CSV** é o único que não representa o dado. A lista `["Python", "SQL"]` teve de virar a string
`"Python, SQL"`, com aspas para escapar a vírgula que também é o separador de campos. Quem lê
recebe uma string e precisa saber, por fora do arquivo, que aquilo era para ser uma lista. CSV
é ótimo para dados tabulares homogêneos e inadequado para qualquer coisa aninhada.

**JSON** é o mais direto: tem array, objeto, número, booleano e `null` como tipos nativos, e a
sintaxe é mínima. É por isso que domina APIs modernas — o custo de gerar e consumir é baixo em
qualquer linguagem.

**XML** é o mais verboso, e a verbosidade compra coisas. Cada valor fica dentro de uma tag
nomeada, existe atributo além de elemento, e há um ecossistema de validação (XSD), consulta
(XPath) e transformação (XSLT). Sobrevive em sistemas legados, integrações bancárias e notas
fiscais exatamente por causa da validação por esquema, não apesar da verbosidade.

**YAML** troca pontuação por indentação. Sem chaves e sem aspas obrigatórias, é o mais confortável
de editar à mão — e o mais fácil de quebrar, porque um espaço a mais muda a estrutura. É o
formato de configuração de Docker Compose, Kubernetes e pipelines de CI.

**TOML** busca o meio-termo: explícito como JSON, legível como YAML, e sem depender de
indentação. É o formato de `pyproject.toml` e `Cargo.toml`, onde a configuração é plana ou
levemente aninhada.

### Comparação resumida

| | CSV | JSON | XML | YAML | TOML |
| --- | :-: | :-: | :-: | :-: | :-: |
| Aninhamento | ✖ | ✔ | ✔ | ✔ | ✔ |
| Tipos nativos | ✖ | ✔ | ✖ (sem XSD) | ✔ | ✔ |
| Comentários | ✖ | ✖ | ✔ | ✔ | ✔ |
| Validação por esquema | ✖ | JSON Schema | XSD | ✖ | ✖ |
| Facilidade de edição manual | média | média | baixa | alta | alta |
| Uso típico | planilhas, exportação | APIs, troca de dados | legado, fiscal, SOAP | configuração, DevOps | configuração de projeto |

---

## Parte 1.2 — Cliente-servidor com sockets TCP

### O problema

Ter o texto serializado não basta: é preciso entregá-lo a outro processo. A parte 1.2 constrói
um par cliente-servidor que transmite **o mesmo registro nos cinco formatos**, em sequência, e
o servidor precisa descobrir sozinho como interpretar cada um.

O conjunto de dados aqui é outro, mais simples que o da parte 1.1, porque o foco mudou: não se
trata mais de comparar estruturas, e sim de transportar bytes.

```python
info_cliente = {
    "nome": "Fulano",
    "cpf": "10326709722",
    "idade": 45,
    "mensagem": "segue comprovante de endereço",
}
```

### O protocolo de aplicação

O TCP entrega um **fluxo de bytes**. Ele garante que os bytes cheguem, na ordem certa e sem
corrupção — e só isso. Ele não diz onde uma mensagem termina nem o que ela contém. Os dois
problemas que sobram para a aplicação são:

1. **Identificação de conteúdo** — como o servidor sabe se aqueles bytes são JSON ou YAML?
2. **Enquadramento** — como o servidor sabe onde uma mensagem acaba e a próxima começa?

O protocolo desta atividade resolve os dois de forma mínima:

```text
CSV|nome,cpf,idade,mensagem\nFulano,10326709722,45,segue comprovante de endereço
└┬┘│└──────────────────────────── payload ────────────────────────────────────┘
 │ └─ separador
 └─ identificador de formato
```

* **Identificação:** o prefixo `FORMATO|` antes do conteúdo. O servidor faz
  `dados.split('|', 1)` e usa o primeiro pedaço para escolher o desserializador.
* **Enquadramento:** o servidor responde `OK` após processar cada mensagem, e o cliente só
  envia a próxima depois de receber essa confirmação. O `ACK` é o que impede as mensagens de
  se juntarem no buffer.

### Fluxo de uma mensagem

```text
   CLIENTE                                    SERVIDOR
      │                                          │
      │  connect()                               │ bind() / listen() / accept()
      │─────────────────────────────────────────►│
      │                                          │
      │  "CSV|nome,cpf,idade,mensagem\n..."      │
      │─────────────────────────────────────────►│ recv(4096)
      │                                          │ split('|', 1)  -> formato, payload
      │                                          │ csv.reader(...) -> dicionário
      │                                          │ imprime os campos
      │  b"OK"                                   │
      │◄─────────────────────────────────────────│ sendall(b"OK")
      │                                          │
      │  (só agora envia JSON, XML, YAML, TOML)  │
```

### Execução

Requer `pyyaml` e `toml`:

```powershell
pip install pyyaml toml
```

Em dois terminais, a partir de [`Atividade-1.2/`](Atividade-1.2/):

```powershell
# terminal 1
python servidor.py

# terminal 2
python cliente.py
```

O servidor precisa subir primeiro: ele abre a porta `65432` em `127.0.0.1` e aceita **uma**
conexão. Quando o cliente termina e fecha o socket, o `recv` devolve vazio e o servidor encerra.

### Saída real

Cliente:

```text
Enviando mensagem formatada em CSV...
Status do servidor: OK

Enviando mensagem formatada em JSON...
Status do servidor: OK

Enviando mensagem formatada em XML...
Status do servidor: OK

Enviando mensagem formatada em YAML...
Status do servidor: OK

Enviando mensagem formatada em TOML...
Status do servidor: OK
```

Servidor (um bloco por mensagem; dois deles reproduzidos abaixo):

```text
----------------------------------------
Recebido formato: JSON
----------------------------------------
Texto Serializado:
{"nome": "Fulano", "cpf": "10326709722", "idade": 45, "mensagem": "segue comprovante de endereço"}

Dados Manipulados (Dicionário Extraído):
  Nome:     Fulano
  CPF:      10326709722
  Idade:    45
  Mensagem: segue comprovante de endereço

----------------------------------------
Recebido formato: YAML
----------------------------------------
Texto Serializado:
cpf: '10326709722'
idade: 45
mensagem: "segue comprovante de endere\xE7o"
nome: Fulano

Dados Manipulados (Dicionário Extraído):
  Nome:     Fulano
  CPF:      10326709722
  Idade:    45
  Mensagem: segue comprovante de endereço
```

Os cinco formatos chegam e são desserializados corretamente. O dicionário reconstruído no
servidor é impresso campo a campo, provando que o ciclo serializar → transmitir →
desserializar fechou.

---

## O que a atividade expõe

Dois achados saíram de medição, não de leitura do código. Os dois são a razão de a AP2 existir.

### 1. Sem o `ACK`, as cinco mensagens viram uma

Para confirmar que o `ACK` não é decoração, as mesmas cinco mensagens foram enviadas em
sequência, sem esperar a confirmação, contra o mesmo `servidor.py`. O resultado:

| | Com `ACK` | Sem `ACK` |
| --- | :-: | :-: |
| Mensagens enviadas | 5 | 5 |
| Blocos processados pelo servidor | **5** | **1** |

O servidor leu tudo em um único `recv(4096)`, aplicou `split('|', 1)` e tratou os 5 envios como
uma só mensagem CSV:

```text
Recebido formato: CSV
Texto Serializado:
nome,cpf,idade,mensagem
Fulano,10326709722,45,segue comprovante de endereçoJSON|{"nome": "Fulano", ...}XML|<cliente>...
```

O pior detalhe é que **não houve erro**. O `csv.reader` leu as duas primeiras linhas, ignorou o
resto, e o servidor imprimiu `Nome: Fulano / Idade: 45` — dados que parecem corretos. Quatro
mensagens foram engolidas em silêncio.

Essa é a lição central da parte 1.2: **"enviei duas mensagens" não significa "chegaram duas
mensagens"**. O TCP é um fluxo, não uma fila de mensagens. Todo protocolo sobre TCP precisa de
uma regra de enquadramento — e o `ACK` desta atividade é a mais simples possível, ao custo de
serializar o envio e pagar um *round-trip* por mensagem.

### 2. Texto não carrega tipo

O campo `idade` sai do cliente como o inteiro `45`. Medindo o que volta no servidor depois de
cada desserialização:

| Formato | Bytes | Linhas | Tipo de `idade` na volta | Não-ASCII (`ç`) |
| --- | ---: | :-: | :-: | --- |
| CSV | 77 | 2 | `str` `'45'` | literal |
| YAML | 86 | 4 | `int` `45` | escapado (`\xE7`) |
| TOML | 90 | 4 | `int` `45` | literal |
| JSON | 103 | 1 | `int` `45` | escapado (`ç`) |
| XML | 128 | 1 | `str` `'45'` | literal |

Duas consequências:

* **CSV e XML perdem o tipo.** Em CSV tudo é célula de texto. Em XML, o nó de texto também é
  string — o cliente precisou fazer `str(valor)` para escrever, e nada no documento diz que
  aquilo era um número. XML só recupera o tipo com um esquema XSD, que esta atividade não usa.
* **JSON, YAML e TOML preservam.** Os três têm tipos escalares no próprio formato, então `45`
  volta como `int`.

Isso significa que, sem um contrato, o receptor precisa **saber por fora** o que cada campo
deveria ser e converter na mão. É exatamente o problema que a AP2 resolve com validação por
modelos Pydantic, e que a [AP4](../Atividade-Pratica-4/README.MD) leva ao extremo com um
contrato `.proto` compilado, onde `int32 dias` é verificado na geração do código.

### Como reproduzir as medições

```python
# com o servidor no ar, envia tudo sem esperar o ACK
for formato, payload in mensagens:
    s.sendall(f"{formato}|{payload}".encode("utf-8"))   # sem o s.recv(1024)
```

```python
# fidelidade de tipos: desserializa e inspeciona
d = json.loads(payload_json)
print(type(d["idade"]).__name__, len(payload_json.encode("utf-8")))
```

---

## Limitações conhecidas

Listadas porque são o ponto de partida das atividades seguintes, não porque sejam defeitos a
corrigir aqui.

| Limitação | Consequência | Resolvida em |
| --- | --- | --- |
| Enquadramento depende do `ACK` | um *round-trip* por mensagem; sem ele, tudo se junta | AP2, com `Content-Length` |
| `recv(4096)` com tamanho fixo | um payload maior que 4096 bytes chega partido | AP2, com o próprio HTTP |
| Identificação por prefixo `FORMATO\|` | convenção informal, não verificada | AP2, com `Content-Type` |
| Servidor atende um cliente só | `accept()` é chamado uma vez, sem laço nem threads | AP2, com servidor ASGI |
| Sem código de erro | falha vira `print` de exceção; o cliente recebe `OK` de qualquer forma | AP2, com status HTTP |
| Sem tipos garantidos | o receptor converte na mão | AP2 (Pydantic) e AP4 (`.proto`) |

---

## Aprendizados

**Sobre serialização.** Não existe formato melhor — existe formato adequado ao uso. A escolha
se resume a três eixos: representa aninhamento? preserva tipos? é editado por humano ou por
programa? CSV falha no primeiro, XML no segundo, e YAML é o melhor no terceiro.

**Sobre TCP.** A garantia do TCP é de entrega ordenada de **bytes**, não de mensagens. Essa
distinção não é um detalhe teórico: ela apareceu como quatro mensagens perdidas em silêncio no
teste sem `ACK`.

**Sobre protocolos.** Construir um protocolo de aplicação do zero significa reinventar
identificação de conteúdo, enquadramento, confirmação e tratamento de erro. Cada um desses foi
resolvido aqui da forma mais simples possível, e cada um tem um equivalente padronizado e mais
robusto no HTTP.

**Sobre a disciplina.** O valor desta atividade é servir de contraste. Ao chegar na AP2, o
cabeçalho `Content-Type` deixa de ser burocracia e passa a ser a versão madura do prefixo
`FORMATO|`; o `Content-Length` passa a ser o enquadramento que o `ACK` improvisava.

---

## Ponte para as atividades seguintes

| | O que a AP1 fez à mão | O que o protocolo padronizado oferece |
| --- | --- | --- |
| Identificar o conteúdo | prefixo `FORMATO\|` | `Content-Type` (AP2), `.proto` (AP4) |
| Delimitar a mensagem | `ACK` do servidor | `Content-Length` (AP2), frames HTTP/2 (AP4) |
| Sinalizar erro | `print` da exceção | status HTTP (AP2), status gRPC (AP4) |
| Garantir tipos | conversão manual | Pydantic (AP2), Protocol Buffers (AP4) |
| Entregar a mais de um destino | um socket, um cliente | broker e tópicos (AP3) |
