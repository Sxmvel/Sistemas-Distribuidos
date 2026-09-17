# Sistemas Distribuídos 🌐

Repositório das atividades práticas da disciplina de **Sistemas Distribuídos**, 6º período do
curso de Sistemas de Informação.

As quatro atividades não são exercícios isolados: elas percorrem, em ordem, os estilos de
comunicação que um sistema distribuído pode adotar — de um protocolo próprio sobre sockets até
chamadas remotas com contrato forte. A partir da Atividade 2, todas modelam **o mesmo domínio**
(o acervo e os empréstimos de uma biblioteca), de propósito: com o problema fixo, o que a
comparação revela é o estilo de comunicação, e não a diferença entre os domínios.

---

## 🧭 O fio condutor

Cada atividade resolve um problema que a anterior deixou exposto.

**A Atividade 1** monta um protocolo próprio sobre TCP. Para o servidor saber o que chegou, o
cliente prefixa o formato (`JSON|{...}`); para as mensagens não se colarem no buffer, o
servidor devolve um `ACK`. Funciona — e deixa claro quanto trabalho existe em inventar um
protocolo do zero.

**A Atividade 2** troca o protocolo próprio pelo HTTP e descobre que aqueles problemas já
tinham solução padronizada: o prefixo `FORMATO|` vira `Content-Type`, o `ACK` que evitava a
junção de pacotes vira `Content-Length`, e os códigos de status substituem convenções
inventadas caso a caso.

**A Atividade 3** ataca outro limite: em REST, o cliente precisa saber quem chamar e esperar a
resposta. Com MQTT e um broker no meio, o terminal publica um empréstimo sem saber que existem
um painel de acervo e um serviço de atrasos ouvindo. O preço é que não existe resposta — e
garantias como "pelo menos uma vez" trazem duplicação junto.

**A Atividade 4** volta ao modelo síncrono, mas com contrato executável: o `.proto` gera o
código dos dois lados, o deadline viaja no protocolo e o status de erro é padronizado. O preço
agora é acoplamento de esquema — cliente e servidor compartilham um artefato gerado.

| | AP1 | AP2 | AP3 | AP4 |
| --- | --- | --- | --- | --- |
| **Estilo** | protocolo próprio | requisição/resposta | publish/subscribe | chamada de procedimento |
| **Transporte** | sockets TCP | HTTP/1.1 | MQTT 5 sobre TCP | HTTP/2 |
| **Contrato** | convenção no código | OpenAPI (descritivo) | tópico + envelope JSON | `.proto` (prescritivo) |
| **Formato** | texto (5 formatos) | JSON | JSON | Protobuf (binário) |
| **Acoplamento** | total | de recurso | de tópico | de esquema e de build |
| **Temporal** | síncrono | síncrono | assíncrono | síncrono |
| **Quem conhece quem** | endereço fixo | cliente conhece a URL | ninguém conhece ninguém | cliente conhece método e endereço |
| **Canal de erro** | nenhum | status HTTP | não existe | status gRPC |

---

## 🛠️ Tecnologias utilizadas

| Camada | AP1 | AP2 | AP3 | AP4 |
| --- | --- | --- | --- | --- |
| Comunicação | `socket` (TCP/IP) | FastAPI / HTTP | `paho-mqtt` (MQTT 5) | `grpcio` / HTTP/2 |
| Serialização | CSV, JSON, XML, YAML, TOML | JSON + Pydantic | JSON (envelope próprio) | Protocol Buffers |
| Persistência | — | SQLite (`sqlite3` puro) | SQLite (deduplicação) | memória com trava |
| Infraestrutura | — | — | Mosquitto 2 em Docker | — |
| Testes | manual | `pytest` (45) | `pytest` (61) | `pytest` (58) |

**Linguagem:** Python em todas as atividades.

---

## 🗂️ Organização do repositório

Cada atividade tem a sua própria pasta e o seu próprio branch, com ambiente virtual e
dependências independentes. Não há nada compartilhado entre elas além do domínio modelado.

```text
Atividade-Pratica-1/   serialização em texto e cliente-servidor com sockets
Atividade-Pratica-2/   API REST com FastAPI e SQLite
Atividade-Pratica-3/   publish/subscribe com MQTT e Mosquitto
Atividade-Pratica-4/   serviço remoto com gRPC e Protocol Buffers
```

As atividades 2, 3 e 4 têm documentação própria e suítes de teste; cada pasta traz o roteiro de
execução no seu README ou em `docs/`.

---

## 🚀 Atividades Realizadas

### 📍 [Atividade Prática 1](Atividade-Pratica-1/README.MD)

#### 1.1 — Formatos de serialização baseados em texto

> Estudo comparativo prático sobre como diferentes linguagens estruturam e serializam a mesma
> informação em texto puro. Com um conjunto de dados padronizado, a atividade evidencia as
> diferenças de sintaxe, o tratamento de estruturas aninhadas e o custo de legibilidade.

* **Conceitos estudados:** serialização e desserialização; representação de tipos em texto;
  aninhamento de estruturas; verbosidade contra legibilidade.
* **Formatos analisados:** [`CSV`](Atividade-Pratica-1/csv.csv),
  [`JSON`](Atividade-Pratica-1/json.json), [`XML`](Atividade-Pratica-1/xml.xml),
  [`YAML`](Atividade-Pratica-1/yaml.yaml) e [`TOML`](Atividade-Pratica-1/toml.toml).
* **Principais aprendizados:** cada formato otimiza uma coisa diferente. CSV é tabular e não
  representa aninhamento; JSON domina APIs modernas por ser simples de gerar e consumir; XML
  sobrevive em sistemas legados e fiscais por causa de esquemas e validação; YAML e TOML
  ganharam espaço em configuração e DevOps por priorizarem a leitura humana.

#### 1.2 — Cliente-servidor com sockets TCP

> Sistema de troca de mensagens em rede que transmite o mesmo conjunto de dados (Nome, CPF,
> Idade, Mensagem) nos cinco formatos, sequencialmente. O
> [cliente](Atividade-Pratica-1/Atividade-1.2/cliente.py) empacota e envia; o
> [servidor](Atividade-Pratica-1/Atividade-1.2/servidor.py) identifica o formato, desserializa
> e imprime os dados já convertidos em dicionário.

* **Conceitos estudados:** sockets TCP/IP; o modelo cliente-servidor; TCP como fluxo de bytes
  sem fronteiras de mensagem; enquadramento (*framing*); confirmação de recebimento.
* **Protocolo de aplicação próprio:** cada mensagem viaja como `FORMATO|payload`. O prefixo é
  o que permite ao servidor escolher o desserializador, já que os bytes chegam sem nenhuma
  indicação de tipo.
* **Controle de fluxo:** o servidor responde `OK` a cada mensagem e o cliente só envia a
  próxima depois disso. Sem esse `ACK`, duas mensagens enviadas em sequência podem ser
  entregues em um único `recv`, porque o TCP garante ordem e entrega — mas não preserva as
  fronteiras de quem enviou.
* **Principais aprendizados:** a percepção central da atividade é que **"enviei duas mensagens"
  não significa "chegaram duas mensagens"**. Todo protocolo de aplicação sobre TCP precisa
  resolver enquadramento e identificação de conteúdo — e é exatamente isso que os protocolos
  padronizados das atividades seguintes já resolvem.

---

### 📍 [Atividade Prática 2](Atividade-Pratica-2/README.MD)

#### API REST de gerenciamento de acervo de biblioteca

> Construção de uma API REST completa sobre HTTP, saindo do protocolo próprio da Atividade 1
> para um protocolo de aplicação padronizado. O domínio é o acervo de uma biblioteca, com duas
> coleções relacionadas: **livros** e os **empréstimos** de cada livro.

A virada conceitual está em perceber que os problemas resolvidos manualmente na Atividade 1 já
tinham solução no HTTP: o prefixo `FORMATO|payload` vira o cabeçalho `Content-Type`, e o `ACK`
que evitava a junção de pacotes no TCP vira o `Content-Length`.

* **Conceitos estudados:** recurso contra representação; semântica dos métodos HTTP;
  idempotência; negociação de conteúdo; concorrência otimista; paginação; observabilidade.
* **Recursos implementados:** 13 endpoints — 10 de domínio cobrindo `GET`, `POST`, `PUT`,
  `PATCH` e `DELETE`, com sub-recurso aninhado (`/v1/livros/{id}/emprestimos`), mais 3 de
  diagnóstico (`/v1/saude`, `/v1/lento`, `/v1/indisponivel`) usados nos experimentos de timeout
  e indisponibilidade.
* **Semântica HTTP:** uso deliberado de `200`, `201`, `204`, `304`, `404`, `409`, `412`, `422`
  e `503`, com `Location` na criação e `Retry-After` na indisponibilidade.
* **Validação:** modelos Pydantic separados para entrada e saída, com `extra="forbid"`
  rejeitando campos desconhecidos em vez de ignorá-los em silêncio.
* **Tratamento de erros:** envelope único em `application/problem+json`, traduzindo erros
  técnicos do banco em erros de domínio sem vazar detalhes internos.
* **Concorrência:** controle otimista com `ETag`/`If-Match` (`412`) e validação condicional com
  `If-None-Match` (`304`), demonstrando a perda de atualização e o mecanismo que a impede.
* **Observabilidade:** log estruturado em JSON com identificador de correlação, método,
  caminho, status e duração de cada requisição.
* **Testes:** 45 testes automatizados em `pytest` e 8 cenários com cliente programático que
  geram a tabela de evidências automaticamente.
* **Principais aprendizados:** a distinção entre recurso e representação; idempotência como
  propriedade do estado final e não da resposta; e a diferença crítica entre *"o servidor
  respondeu erro"* e *"o cliente não obteve resposta"* — a segunda deixa o cliente sem saber se
  a operação chegou a ser executada. Essa dúvida reaparece, medida, na Atividade 4.

---

### 📍 [Atividade Prática 3](Atividade-Pratica-3/README.MD)

#### Publish/subscribe com MQTT e broker Mosquitto

> Mesma biblioteca, outro estilo: em vez de um cliente chamando um servidor, um **terminal de
> autoatendimento** publica eventos de empréstimo e devolução em tópicos, e dois consumidores
> independentes — um **painel de acervo** e um **serviço de atrasos** — reagem a eles sem que o
> publicador saiba que existem.

A pergunta que organiza a atividade é o que exatamente o broker desacopla, e quanto custa cada
garantia de entrega que ele oferece.

* **Conceitos estudados:** desacoplamento espacial, temporal e de sincronia; roteamento por
  tópicos e curingas; níveis de QoS; mensagem retida; Last Will; sessão persistente contra
  efêmera; deduplicação idempotente; *backpressure*.
* **Taxonomia de tópicos:** `biblioteca/{unidade}/{terminal}/{evento}`, com filtros por
  curinga (`biblioteca/+/+/emprestimo`) validados por testes. A hierarquia é o que permite a um
  consumidor assinar uma unidade inteira sem conhecer os terminais.
* **Envelope versionado:** toda mensagem carrega `message_id`, `producer_id`, `sequence`,
  `schema_version`, `timestamp` e `data`. Como não existe contrato no protocolo, o envelope
  é o contrato — e o `schema_version` é o que permite evoluí-lo.
* **Infraestrutura:** Mosquitto 2 em Docker Compose, com persistência habilitada, expiração de
  sessão e fila limitada, para que os experimentos de queda e de retomada sejam reproduzíveis.
* **Resiliência do cliente:** reconexão com *backoff* exponencial e *jitter*, parada limpa e
  `Last Will` registrado no CONNECT.
* **Sete experimentos automatizados**, cada um respondendo a uma pergunta:

  | | Experimento | Pergunta |
  | --- | --- | --- |
  | E01 | Desacoplamento e roteamento por tópicos | O que exatamente foi desacoplado pelo broker? |
  | E02 | QoS 0 contra QoS 1 com o broker fora | O QoS escolhido é suficiente para o requisito? |
  | E03 | Retained como último valor conhecido | Quando retained é apropriado e quando é perigoso? |
  | E04 | Last Will e desconexão anormal | Como o sistema percebe que um produtor caiu sem avisar? |
  | E05 | Duplicação em QoS 2 e deduplicação | Como o sistema identifica mensagem duplicada? |
  | E06 | Consumidor lento e backpressure | A lentidão do consumidor vira perda ou atraso? |
  | E07 | Sessão persistente contra efêmera | O que acontece com o que foi produzido enquanto o consumidor estava fora? |

* **Testes:** 61 testes de `pytest` sobre o envelope, a taxonomia de tópicos e a deduplicação.
* **Principais aprendizados:** o broker desacopla **quem** e **quando**, mas não o **formato** —
  o acoplamento migra da URL para o envelope. QoS 1 é *pelo menos uma vez*, e "pelo menos uma"
  significa que duplicar é comportamento esperado, não falha: só a deduplicação por
  `message_id` evita cobrar a mesma multa duas vezes. E a lentidão de um consumidor não vira
  perda, vira fila — até a fila estourar.

---

### 📍 [Atividade Prática 4](Atividade-Pratica-4/README.MD)

#### Serviço remoto de empréstimos com gRPC e Protocol Buffers

> A mesma biblioteca de novo, agora como chamada de procedimento remoto. O contrato é escrito
> primeiro, em um arquivo `.proto`, e o código do cliente e do servidor é **gerado** a partir
> dele. A atividade gira em torno de uma pergunta: o que a abstração de "chamada de função"
> esconde, e o que acontece quando ela vaza.

* **Conceitos estudados:** a ilusão de chamada local; IDL e geração de *stubs*; *marshalling* e
  formato binário; tipos de RPC; deadlines e cancelamento; propagação de orçamento de tempo;
  modelo de status de erro; idempotência e retry seguro; evolução de contrato; interceptors.
* **Contrato:** 5 métodos RPC e 11 mensagens próprias em
  [`emprestimos.proto`](Atividade-Pratica-4/contratos/emprestimos.proto) — quatro chamadas
  unárias e uma de *server streaming*. A geração dos stubs é reproduzível do zero, verificada
  por comparação de hash SHA-256.
* **Modelo de erro:** erros de domínio traduzidos em um único ponto para `INVALID_ARGUMENT`,
  `NOT_FOUND`, `FAILED_PRECONDITION` e `ALREADY_EXISTS`, com o campo inválido devolvido no
  *trailing metadata*. Cada status carrega a política de retry que ele implica.
* **Interceptors:** correlação e métricas nas duas pontas, mais a tradução de erro no servidor.
  O serviço não decide códigos de status; a regra de negócio continua visível e testável.
* **Evolução de contrato:** três versões do `.proto` no repositório — a atual, a anterior e um
  contra-exemplo com mudanças proibidas — usadas para medir o que preserva clientes antigos e o
  que os quebra.
* **Sete experimentos automatizados**, com 90 verificações e uma tabela de latência e status por
  chamada gerada a cada execução:

  | | Experimento | O que demonstra |
  | --- | --- | --- |
  | E01 | Contrato, stubs e fluxo unário/streaming | stubs byte a byte idênticos ao regenerar |
  | E02 | Erros de domínio contra status gRPC | cinco status distintos para causas distintas |
  | E03 | Deadlines de 100 ms, 1 s e 3 s | o servidor abandona a chamada em 4 de 40 itens |
  | E04 | Indisponibilidade do servidor | mesmo pedido, dois eixos de erro diferentes |
  | E05 | Concorrência e `max_workers` | p95 cai de ~1,2 s para ~0,3 s; 12 clientes, 1 exemplar |
  | E06 | Retry após deadline ambíguo | sem chave o retry duplica; com chave, não |
  | E07 | Evolução de contrato | mudança incompatível corrompe em silêncio |

* **Testes:** 58 testes de `pytest`, subindo o servidor em porta efêmera dentro do processo.
* **Principais aprendizados:** três medições resumem a atividade. **(1)** O cliente registrou
  `DEADLINE_EXCEEDED` para uma chamada que o servidor concluiu com `OK` — uma chamada remota
  tem um terceiro resultado além de "deu certo" e "deu erro": *não se sabe*. **(2)** O mesmo
  pedido inválido devolve `INVALID_ARGUMENT` com o servidor no ar e `UNAVAILABLE` com ele fora,
  o que separa erro de aplicação de falha de infraestrutura. **(3)** As mudanças incompatíveis
  no `.proto` não levantam exceção nenhuma: reaproveitar um número de campo faz o dado chegar
  corrompido, e trocar o tipo faz o valor sumir — as duas em silêncio.

---

## 🔍 Síntese comparativa

O mesmo problema, resolvido em três estilos, deixa as diferenças em evidência.

### Onde mora a garantia de não duplicar

| Atividade | Mecanismo | Nível |
| --- | --- | --- |
| AP2 — REST | `PUT` idempotente por definição; `If-Match` com `ETag` | **protocolo** |
| AP3 — MQTT | `message_id` no envelope, deduplicado por cada consumidor | **mensagem** |
| AP4 — gRPC | campo `chave_idempotencia` guardado com a impressão do pedido | **aplicação** |

gRPC é o que menos ajuda: não existe "método idempotente" no protocolo, todo RPC é uma chamada
opaca. A ambiguidade do `DEADLINE_EXCEEDED` é a mesma de um `POST` que deu timeout — mas o HTTP
ao menos oferece verbos com semântica combinada.

### Onde o contrato é verificado

| Atividade | Contrato | Quando o erro aparece |
| --- | --- | --- |
| AP1 | convenção no código | em execução, se aparecer |
| AP2 | OpenAPI + Pydantic | em execução, na validação da requisição |
| AP3 | envelope JSON versionado | em execução, no consumidor |
| AP4 | `.proto` compilado | na geração do código — mas renumerar campo escapa até disso |

### O que cada estilo torna fácil, e o que torna difícil

* **REST** é fácil de consumir por qualquer cliente e legível sem ferramenta; em troca, o
  contrato é documentação, e quebrá-lo só aparece em produção.
* **MQTT** é o único que permite adicionar um consumidor novo sem tocar no publicador; em
  troca, não tem resposta nem canal de erro, e obriga a construir à mão a deduplicação e o
  versionamento que os outros recebem prontos.
* **gRPC** dá contrato executável, deadline no protocolo e status padronizado; em troca, exige
  gerar stubs, não é legível em log, e tem armadilhas de evolução que formato de texto não tem.

A conclusão das quatro atividades é que eles não competem. Um sistema real de biblioteca usaria
os três ao mesmo tempo: **REST na borda** para o catálogo público, **gRPC entre serviços**
internos, e **MQTT para propagar** o que aconteceu.
