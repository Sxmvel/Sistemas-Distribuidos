# AP3 — Mensageria com MQTT e broker Mosquitto

Sistema publish/subscribe construído com MQTT 5 e Mosquitto para a Atividade Prática 3 de
Sistemas Distribuídos. O domínio é o mesmo da [AP2](../Atividade-Pratica-2/README.MD) — o acervo
de uma biblioteca — de propósito: com o problema fixo, o que a comparação revela é a mudança de
estilo de comunicação.

A atividade demonstra desacoplamento por tópicos, os três níveis de QoS, mensagem retida, Last
Will, sessão persistente, deduplicação idempotente e o comportamento do sistema sob consumidor
lento e consumidor ausente.

---

## O problema que a atividade resolve

A AP2 entregou uma API REST funcionando, e com ela três amarras que só aparecem quando o
sistema cresce:

1. **O cliente precisa saber quem chamar.** A URL do servidor está no código do cliente.
2. **Um pedido, um destinatário.** Se três serviços precisam saber que um livro foi emprestado,
   alguém faz três chamadas — e passa a conhecer os três.
3. **Os dois lados precisam estar no ar ao mesmo tempo.** Se o servidor caiu, a informação se
   perde ou o cliente trava esperando.

O MQTT ataca as três com a mesma ideia: colocar um **broker** no meio. O terminal de
autoatendimento publica em um tópico e encerra o assunto. Quem quiser saber, assina. O
publicador não sabe quantos consumidores existem, nem se existe algum, nem se estão no ar.

O que se ganha e o que se paga:

| | REST (AP2) | MQTT (AP3) |
| --- | --- | --- |
| Quem conhece quem | cliente conhece a URL | ninguém conhece ninguém |
| Destinatários | um por requisição | quantos assinarem |
| Disponibilidade | os dois no ar | o broker absorve a ausência |
| Resposta | sempre há uma | **não existe** |
| Erro | status HTTP | **não existe canal de erro** |
| Contrato | OpenAPI | o envelope da mensagem |
| Entrega | uma tentativa | QoS 0, 1 ou 2 |

As duas linhas em negrito são o preço. Sem resposta e sem canal de erro, tudo o que o HTTP dava
de graça — confirmação, código de status, correlação entre pedido e resposta — precisa ser
reconstruído dentro da mensagem ou simplesmente não existe.

## Conceitos estudados

| Conceito | Onde aparece |
| --- | --- |
| Desacoplamento espacial | o publicador não referencia nenhum consumidor (E01) |
| Desacoplamento temporal | a sessão persistente entrega o que foi produzido com o consumidor fora (E07) |
| Roteamento por tópicos | hierarquia `biblioteca/{unidade}/{terminal}/{evento}` e curingas `+` e `#` |
| QoS 0, 1 e 2 | no máximo uma vez, pelo menos uma vez, exatamente uma vez (E02, E05) |
| Duplicação como comportamento esperado | QoS 1 e 2 e a retentativa do produtor (E05) |
| Idempotência no consumidor | deduplicação por `message_id` (E05) |
| Mensagem retida | último valor conhecido para assinantes tardios (E03) |
| Last Will and Testament | detecção de queda sem `DISCONNECT` (E04) |
| Sessão persistente contra efêmera | o que o broker guarda para quem saiu (E07) |
| Backpressure | consumidor lento vira fila e atraso, não perda (E06) |
| Contrato sem protocolo | envelope versionado com `schema_version` |
| Reconexão resiliente | backoff exponencial com jitter |

---

## Arquitetura

```text
                          ┌──────────────────────────┐
   terminais              │        MOSQUITTO         │        consumidores
   (publicadores)         │      (broker MQTT 5)     │        (assinantes)
                          │                          │
  ┌───────────┐  publish  │  biblioteca/             │  subscribe  ┌────────────────┐
  │ term-01   │──────────►│    central/              │◄────────────│ painel-acervo  │
  │ (central) │           │      term-01/            │  +/+/empre. │ (circulação)   │
  └───────────┘           │        emprestimo        │  +/+/devol. └────────────────┘
                          │        devolucao         │
  ┌───────────┐  publish  │        status  (retained)│  subscribe  ┌────────────────┐
  │ term-03   │──────────►│    anexo/                │◄────────────│ servico-atrasos│
  │ (anexo)   │           │      term-03/ ...        │  biblioteca/#│ (multas+SQLite)│
  └───────────┘           └──────────────────────────┘             └────────────────┘
        │                                                                    │
        └── Last Will registrado no CONNECT ──────────────────────────────────┘
            (publicado pelo broker se a conexão cair sem DISCONNECT)
```

Nenhum dos três módulos importa os outros. O `terminal.py` não contém a string
`painel_acervo` em lugar nenhum — o E01 verifica isso lendo o próprio código-fonte.

### Taxonomia de tópicos

```text
biblioteca / {unidade} / {terminal} / {evento}
    raiz        central     term-01     emprestimo | devolucao | status
```

A hierarquia é o que permite assinar em níveis diferentes de granularidade:

| Filtro | Quem usa | O que recebe |
| --- | --- | --- |
| `biblioteca/+/+/emprestimo` | painel de acervo | empréstimos de qualquer terminal de qualquer unidade |
| `biblioteca/+/+/devolucao` | painel de acervo | devoluções de qualquer terminal |
| `biblioteca/#` | serviço de atrasos | tudo, inclusive `status` |
| `biblioteca/central/+/+` | — | toda a unidade central |

[`app/topicos.py`](app/topicos.py) monta e decompõe tópicos com validação: um nível não pode ser
vazio nem conter `/`, `+` ou `#`, porque isso transformaria um dado em um curinga e faria a
mensagem vazar para assinantes errados.

### O envelope

MQTT não define formato de payload — para o broker, é um vetor de bytes. Como não há contrato
no protocolo, **o envelope é o contrato**:

```json
{
  "message_id": "9f2c...",          identificador único, base da deduplicação
  "producer_id": "term-01",         quem produziu
  "sequence": 42,                   ordem por produtor, revela lacunas
  "schema_version": 1,              permite evoluir o formato
  "timestamp": "2026-09-16T...",    permite medir atraso fim a fim
  "data": { "acao": "emprestimo", "isbn": "...", "leitor": "..." }
}
```

[`app/envelope.py`](app/envelope.py) valida na desserialização: campos obrigatórios presentes,
`sequence` inteiro não negativo, `data` objeto, e `schema_version` **menor ou igual** à versão
conhecida. Essa última regra é a regra de evolução: um consumidor antigo recusa explicitamente
uma mensagem de esquema mais novo em vez de processá-la pela metade.

`RastreadorDeSequencia` classifica cada chegada como `primeira`, `em-ordem`, `repetida`,
`lacuna` ou `fora-de-ordem`. É assim que o consumidor percebe perda — o broker nunca avisa.

---

## Execução

### 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Broker

Requer Docker Desktop no ar.

```powershell
docker compose up -d mosquitto
```

Sobe `eclipse-mosquitto:2` na porta `1883`, configurado por
[`mosquitto/mosquitto.conf`](mosquitto/mosquitto.conf) com persistência habilitada, expiração
de sessão de 1 h e fila de até 10 000 mensagens — os três parâmetros que tornam os experimentos
de queda e de retomada reproduzíveis.

```powershell
docker compose logs -f mosquitto   # acompanhar
docker compose down -v             # derrubar e limpar o estado
```

### 3. Testes automatizados

Não dependem do broker:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

61 testes cobrindo a validação do envelope, a taxonomia de tópicos com curingas e a
deduplicação idempotente.

### 4. Experimentos

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos
```

Sobe o broker, limpa o estado anterior, roda os sete cenários em sequência e grava a tabela de
evidências em `docs/04-evidencias.md`. Para rodar apenas alguns:

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos E02 E05
```

### 5. Execução manual

Em terminais separados, com o broker no ar:

```powershell
# consumidor 1 — painel de circulação
.\.venv\Scripts\python.exe -m app.assinantes.painel_acervo

# consumidor 2 — serviço de atrasos e multas
.\.venv\Scripts\python.exe -m app.assinantes.servico_atrasos

# produtor — terminal de autoatendimento
.\.venv\Scripts\python.exe -m app.publicadores.terminal --unidade central --terminal term-01 --mensagens 40
```

Suba os consumidores **antes** do produtor. Sem sessão persistente, o que é publicado antes da
assinatura não chega a ninguém — e essa é justamente a demonstração do E07.

#### Opções do produtor

| Opção | Uso |
| --- | --- |
| `--unidade`, `--terminal` | compõem o tópico de publicação |
| `--qos 0\|1\|2` | nível de entrega do `publish` |
| `--mensagens`, `--intervalo` | volume e ritmo da carga |
| `--semente` | torna a sequência de movimentações determinística |
| `--reenviar-a-cada N` | republica a mesma mensagem a cada N, simulando retentativa (E05) |
| `--manter-vivo` | não encerra ao terminar, para poder matar o processo (E04) |

#### Opções dos consumidores

| Opção | Uso |
| --- | --- |
| `--qos` | QoS pedido na assinatura |
| `--filtro` | um ou mais filtros de tópico, substituindo o padrão |
| `--sessao-persistente` / `--sessao-efemera` | o broker guarda ou descarta o que chegou com o cliente fora |
| `--lento S` | atraso artificial por mensagem, para provocar backpressure (E06) |
| `--sem-deduplicacao` | desliga o descarte por `message_id`, para mostrar o efeito (E05) |
| `--ate-mensagens`, `--duracao` | critérios de parada automática |

---

## Os sete experimentos

Cada cenário responde a uma pergunta e grava as suas verificações na tabela de evidências.

| | Título | Pergunta | O que demonstra |
| :-: | --- | --- | --- |
| **E01** | Desacoplamento e roteamento por tópicos | O que exatamente foi desacoplado? | Dois terminais publicam; os dois consumidores recebem tudo sem que o produtor os conheça. O painel não recebe `status` porque o seu filtro não cobre esse nível; o serviço de atrasos recebe, porque assina `biblioteca/#`. O mesmo filtro que desacopla também **decide o que você não vê**. |
| **E02** | QoS 0 contra QoS 1 com o broker fora | O QoS escolhido atende ao requisito? | A mesma carga de 60 mensagens, com o broker parado por 3 s no meio. Em QoS 0 o `publish` sem conexão retorna `NO_CONN` e a mensagem some. Em QoS 1 ela fica na fila do cliente e é reenviada na reconexão. |
| **E03** | Retained como último valor conhecido | Quando retained é apropriado e quando é perigoso? | Um assinante que chega depois recebe o **último** `status` publicado — não o histórico. E continua recebendo mesmo com o produtor morto: útil para estado, perigoso se alguém confundir "retido" com "atual". |
| **E04** | Last Will e desconexão anormal | Como o sistema percebe que um produtor caiu sem avisar? | O terminal registra um testamento no CONNECT e é morto sem `DISCONNECT`. O broker publica o testamento com `estado: offline` e `motivo: desconexao-anormal`, distinguível do `encerramento-programado` que o próprio terminal publica ao sair de forma limpa. |
| **E05** | Duplicação em QoS 2 e deduplicação | Como identificar mensagem duplicada? | O centro da análise. Mesmo em **QoS 2**, uma retentativa do produtor chega como entrega nova — porque "exatamente uma vez" vale para a entrega de um `publish`, não para dois `publish` do mesmo conteúdo. Só a deduplicação por `message_id` evita cobrar a multa duas vezes. |
| **E06** | Consumidor lento e backpressure | A lentidão vira perda ou atraso? | Rajada de 60 mensagens com um consumidor lento e um rápido. Os dois recebem tudo; o que muda é o atraso fim a fim, medido pelo `timestamp` do envelope. A lentidão vira fila — até a fila estourar. |
| **E07** | Sessão persistente contra efêmera | O que acontece com o produzido enquanto o consumidor estava fora? | Com os dois consumidores derrubados, 60 mensagens são publicadas. Na volta, a sessão persistente recupera tudo; a efêmera não recupera nada, porque o broker descartou a assinatura junto com a sessão. |

> As evidências ficam em `docs/04-evidencias.md`, **gerado** pela execução. O arquivo ainda não
> está no repositório: rode `python -m experimentos.executar_todos` com o Docker Desktop no ar
> para produzi-lo.

---

## Estrutura

```text
Atividade-Pratica-3/
├── app/
│   ├── config.py          endereço do broker, QoS padrão, versão do esquema, multa por dia
│   ├── acervo.py          livros, leitores e unidades do domínio
│   ├── topicos.py         taxonomia, validação de níveis e casamento de curingas
│   ├── envelope.py        envelope versionado, sequenciador e rastreador de lacunas
│   ├── conexao.py         cliente MQTT 5, backoff com jitter, Last Will, parada limpa
│   ├── registro.py        log estruturado JSONL, um arquivo por processo
│   ├── persistencia.py    SQLite: mensagens, estoque, multas e estado dos terminais
│   ├── publicadores/
│   │   └── terminal.py    terminal de autoatendimento
│   └── assinantes/
│       ├── painel_acervo.py    circulação em tempo real, em memória
│       └── servico_atrasos.py  multas com deduplicação, em SQLite
├── experimentos/          os sete cenários + orquestrador
├── testes/                61 testes de pytest
├── mosquitto/             configuração do broker
└── compose.yaml           eclipse-mosquitto:2
```

Os dois consumidores são deliberadamente diferentes: o **painel** mantém estado em memória e é
descartável; o **serviço de atrasos** persiste em SQLite e precisa ser idempotente, porque
cobrar multa duas vezes é um erro visível para o usuário. Só o segundo deduplica — e é essa
assimetria que torna o E05 legível.

---

## Decisões de projeto

**MQTT 5, não 3.1.1.** A versão 5 traz `SessionExpiryInterval` explícito, códigos de razão nas
respostas e propriedades no CONNECT. Sem ela, "sessão persistente" dependeria só do flag
`cleanSession`, sem controle de por quanto tempo o broker guarda a fila.

**Envelope próprio em vez de payload cru.** Publicar `{"isbn": "...", "leitor": "..."}` direto
funcionaria — e deixaria o consumidor sem como detectar duplicata, sem como perceber lacuna e
sem como recusar um formato mais novo. Os quatro campos de metadado existem cada um para
resolver um desses problemas.

**Deduplicação no consumidor, não no broker.** O broker não tem como saber que duas mensagens
com `message_id` diferente são a mesma movimentação de negócio. Em contrapartida, o consumidor
sabe — e por isso o `message_id` é `PRIMARY KEY` na tabela `mensagens`, e o `INSERT OR IGNORE`
decide em uma operação atômica se a mensagem é nova.

**`status` retido, movimentações não.** Estado (`online`/`offline` de um terminal) tem um valor
"atual" que faz sentido entregar a quem chega depois. Um empréstimo não — ele é um evento, e
reentregar o último empréstimo a cada novo assinante daria a impressão de que ele acabou de
acontecer.

**Log estruturado por processo.** Cada processo grava `logs/<id>.jsonl`, uma linha por evento.
Como não existe requisição-resposta para correlacionar, a reconstrução do que aconteceu depende
inteiramente desses arquivos — e é sobre eles que os experimentos fazem as suas afirmações.

**Sequência por produtor.** O `sequence` é contado por terminal, não globalmente. Um contador
global exigiria coordenação entre produtores, que é exatamente o que o estilo pub/sub evita.

---

## Aprendizados

**O broker desacopla quem e quando, não o quê.** O acoplamento não desaparece: ele migra. Em
REST estava na URL; aqui está no **nome do tópico** e no **formato do envelope**. Um consumidor
que assina `biblioteca/+/+/emprestimo` depende de o produtor continuar publicando naquele nível
exato — renomear um nível quebra todo mundo, em silêncio e sem erro.

**"Pelo menos uma vez" significa que duplicar é normal.** QoS 1 não é uma entrega com defeito
ocasional: a duplicação é parte da definição. E o E05 mostra que nem QoS 2 resolve o problema
de negócio — ele garante que *aquele* `publish` chegue uma vez só, mas um produtor que
republica depois de um timeout emite um `publish` novo, com `message_id` novo, que o broker
entrega corretamente uma vez. A idempotência tem de estar no consumidor.

**Ausência de resposta muda o desenho inteiro.** Sem retorno, o produtor não sabe se alguém
processou, se houve erro de validação ou se o consumidor está no ar. Tudo o que na AP2 era um
código de status vira, aqui, ou um tópico de status separado, ou nada. Essa é a diferença mais
profunda entre os dois estilos, e não é uma questão de sintaxe.

**Lentidão não vira perda — vira fila.** É contraintuitivo até medir. Um consumidor lento
continua recebendo tudo; o que cresce é o atraso entre o `timestamp` do envelope e o instante
do processamento. O sistema só perde quando a fila do broker estoura o limite configurado, e aí
perde de uma vez.

**Mensagem retida é uma faca de dois gumes.** Ela resolve o problema real de "cheguei agora e
não sei o estado do sistema". E cria outro: o valor continua sendo servido depois de o produtor
morrer, sem nenhuma marca de que está velho. Sem o Last Will para corrigir o estado, um painel
mostraria `online` para um terminal desligado há horas.

**Consumidor tem de perceber sozinho o que o broker não conta.** Não há aviso de mensagem
perdida. O `sequence` por produtor é o único mecanismo que transforma "faltou a 43" em
informação — e ele precisou ser construído dentro do envelope porque o protocolo não oferece
nada equivalente.

---

## Ponte para a AP4

A AP3 resolve o acoplamento da AP2 e cria as suas próprias lacunas:

| Limite da AP3 | Consequência | Resolvido na [AP4](../Atividade-Pratica-4/README.MD) |
| --- | --- | --- |
| Não existe resposta | perguntar "quantos exemplares restam?" exige inventar tópico de pergunta e de resposta | RPC unário: uma requisição, uma resposta |
| Não existe canal de erro | validação falha em silêncio no consumidor | status gRPC com `details` e campo inválido |
| Contrato é convenção no envelope | formato errado só aparece em execução | `.proto` compilado nas duas pontas |
| JSON em texto | payload maior e sem tipo garantido | Protocol Buffers binário, tipado |
| Sem limite de tempo | o consumidor processa quando puder | deadline propagado, com cancelamento observado no servidor |

E confirma, pelo caminho, que a idempotência é um problema que não desaparece: na AP2 ela mora
no protocolo (`PUT`, `If-Match`), na AP3 na mensagem (`message_id`), e na AP4 na aplicação
(chave de idempotência). Três estilos, três lugares, o mesmo problema.
