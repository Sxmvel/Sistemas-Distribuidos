# AP2 — API REST de gerenciamento de acervo de biblioteca

API REST construída com FastAPI e SQLite para a Atividade Prática 2 de Sistemas Distribuídos.
O domínio é o acervo de uma biblioteca, escolhido por ser diferente do exemplo de dispositivos
e leituras da apostila.

A atividade demonstra modelagem de recursos, semântica HTTP, validação de entrada, tratamento
explícito de erros, concorrência otimista com `ETag`/`If-Match`, observabilidade com log
estruturado e testes de comportamento.

---

## O problema que a atividade resolve

A [AP1](../Atividade-Pratica-1/README.MD) construiu um protocolo de aplicação do zero sobre
sockets TCP e, ao fazer isso, expôs tudo o que um protocolo precisa resolver: identificar o
conteúdo, delimitar a mensagem, confirmar o recebimento e sinalizar erro. Cada um desses
problemas foi resolvido lá com uma convenção improvisada — o prefixo `FORMATO|`, um `ACK` de
dois bytes, um `print` de exceção.

A AP2 troca o protocolo próprio pelo HTTP e a descoberta central é que **aqueles problemas já
estavam resolvidos, e melhor**:

| Problema | Solução improvisada na AP1 | Solução padronizada na AP2 |
| --- | --- | --- |
| O que são estes bytes? | prefixo `FORMATO\|` | cabeçalho `Content-Type` |
| Onde a mensagem termina? | `ACK` do servidor a cada mensagem | `Content-Length` |
| Deu certo? | sempre `OK`, mesmo com exceção | código de status HTTP |
| O que exatamente falhou? | texto livre no console do servidor | corpo `application/problem+json` |
| Como saber se mudou? | não havia como | `ETag` e requisições condicionais |

Mas adotar HTTP não é só trocar de biblioteca. O protocolo traz um modelo junto — **recursos
identificados por URL, manipulados por um conjunto fixo de métodos com semântica definida** — e
a atividade consiste em modelar a biblioteca dentro desse modelo, respeitando o que cada método
promete.

## Conceitos estudados

| Conceito | Onde aparece |
| --- | --- |
| Recurso contra representação | um livro tem uma URL; o JSON devolvido é uma de suas representações |
| Interface uniforme | os mesmos cinco métodos valem para livros e empréstimos |
| Semântica dos métodos | `PUT` substitui, `PATCH` altera em parte, `DELETE` remove |
| Idempotência | propriedade do **estado final**, não da resposta — `DELETE` repetido devolve 404, e ainda é idempotente |
| Sub-recurso aninhado | `/v1/livros/{id}/emprestimos` expressa a relação 1 para N na própria URL |
| Códigos de status como contrato | 409 e 412 dizem coisas diferentes, e o cliente age diferente em cada |
| Negociação e envelope de erro | `application/problem+json` em vez de um JSON de erro inventado |
| Concorrência otimista | `ETag` + `If-Match` detectam escrita sobre versão antiga (412) |
| Cache condicional | `If-None-Match` evita transferir o que o cliente já tem (304) |
| Paginação | coleção grande não cabe em uma resposta; página, tamanho e limite máximo |
| Observabilidade | log estruturado com identificador de correlação por requisição |
| Erro de aplicação contra falha de transporte | `503` é resposta; `ConnectionError` é ausência de resposta |

---

## Execução

### 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se a ativação falhar, todos os comandos funcionam com o caminho explícito do interpretador:
`.\.venv\Scripts\python.exe` no lugar de `python`.

### 2. Dados de teste

```powershell
python seed.py
```

Cria `biblioteca.db` com 12 livros e 4 empréstimos ativos. Pode ser executado novamente a
qualquer momento para restaurar o estado inicial.

### 3. Servidor

```powershell
.\.venv\Scripts\fastapi.exe dev app\main.py
```

| Endereço | Conteúdo |
| --- | --- |
| `http://127.0.0.1:8000` | API |
| `http://127.0.0.1:8000/docs` | documentação interativa |
| `http://127.0.0.1:8000/openapi.json` | contrato OpenAPI |

### 4. Verificação rápida

```powershell
curl.exe -i http://127.0.0.1:8000/v1/saude
```

No PowerShell é necessário escrever `curl.exe` com a extensão: `curl` sem ela é apelido para
`Invoke-WebRequest`, que não aceita as mesmas opções.

---

## Testes

### Suíte automatizada

```powershell
.\.venv\Scripts\python.exe -m pytest
```

45 testes cobrindo CRUD, erros, paginação, filtros, empréstimos, invariantes de contrato e
concorrência. Usa `TestClient` com banco temporário, sem depender do servidor no ar.

### Cenários com o cliente programático

Com o servidor rodando em outro terminal:

```powershell
.\.venv\Scripts\python.exe -m cliente.executar_todos
```

Executa os 8 cenários, imprime o resultado de cada verificação e grava a tabela de evidências
em [`docs/04-evidencias.md`](docs/04-evidencias.md).

| Cenário | O que demonstra |
| --- | --- |
| C01 | fluxo completo de criação, empréstimo e devolução |
| C02 | validação de entrada e o envelope de erro (422) |
| C03 | recurso inexistente em todas as formas (404) |
| C04 | conflito com o estado atual (409) |
| C05 | idempotência de POST, PUT e DELETE |
| C06 | perda de atualização e como o `ETag` a impede (304, 412) |
| C07 | timeout do cliente sob três limites diferentes |
| C08 | `ConnectionError` versus `503` |

### Requisições avulsas

- [`curl/requisicoes.http`](curl/requisicoes.http) — para a extensão REST Client do VS Code
- [`curl/requisicoes.sh`](curl/requisicoes.sh) — roteiro em `curl`, executável no Git Bash

---

## Endpoints

| # | Método | Caminho | Sucesso | Erros |
| :-: | --- | --- | --- | --- |
| 1 | GET | `/v1/livros` | 200 | 422 |
| 2 | POST | `/v1/livros` | 201 | 409, 422 |
| 3 | GET | `/v1/livros/{id}` | 200, 304 | 404 |
| 4 | PUT | `/v1/livros/{id}` | 200 | 404, 409, 412, 422 |
| 5 | PATCH | `/v1/livros/{id}` | 200 | 404, 409, 412, 422 |
| 6 | DELETE | `/v1/livros/{id}` | 204 | 404, 409, 412 |
| 7 | GET | `/v1/livros/{id}/emprestimos` | 200 | 404 |
| 8 | POST | `/v1/livros/{id}/emprestimos` | 201 | 404, 409, 422 |
| 9 | GET | `/v1/emprestimos/{id}` | 200 | 404 |
| 10 | PATCH | `/v1/emprestimos/{id}` | 200 | 404, 409, 422 |
| 11 | GET | `/v1/saude` | 200 | 503 |
| 12 | GET | `/v1/lento` | 200 | — |
| 13 | GET | `/v1/indisponivel` | — | 503 |

Treze endpoints ao todo: dez de domínio (1 a 10) e três de diagnóstico (11 a 13). Os de
diagnóstico não fazem parte do modelo da biblioteca — existem para que os cenários C07 e C08
possam provocar timeout e indisponibilidade de forma determinística.

Detalhamento de parâmetros, corpos e cabeçalhos em
[`docs/03-contrato-da-api.md`](docs/03-contrato-da-api.md).

---

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [00 - Índice](docs/00-indice.md) | mapa de cada conceito da apostila até o arquivo que o implementa |
| [01 - Fundamentos REST](docs/01-fundamentos-rest.md) | estilo arquitetural, interface uniforme, métodos e status |
| [02 - Modelagem](docs/02-modelagem-do-dominio.md) | recursos, relações e as decisões de esquema justificadas |
| [03 - Contrato](docs/03-contrato-da-api.md) | cada endpoint em detalhe: parâmetros, corpo, status e cabeçalhos |
| [04 - Evidências](docs/04-evidencias.md) | tabela gerada pela execução dos cenários |
| [05 - Análise](docs/05-questoes-de-analise.md) | as quatro questões da atividade, respondidas |
| [06 - Glossário](docs/06-glossario.md) | termos usados no projeto |

---

## Estrutura

```text
Atividade-Pratica-2/
├── app/
│   ├── main.py               montagem da aplicação, middleware e roteadores
│   ├── db.py                 esquema SQLite, conexão e transação
│   ├── esquemas.py           modelos Pydantic de entrada e saída
│   ├── erros.py              erros de domínio e tradução para problem+json
│   ├── observabilidade.py    log estruturado e identificador de correlação
│   ├── concorrencia.py       ETag, If-Match e If-None-Match
│   ├── paginacao.py          página, tamanho e limite máximo
│   ├── repositorios/         SQL parametrizado e regras de negócio
│   └── rotas/                tradução entre HTTP e domínio
├── cliente/
│   ├── comum.py              sessão com timeout e coletor de evidências
│   ├── cenarios/             os 8 cenários de teste
│   └── executar_todos.py     executa tudo e gera a tabela de evidências
├── testes/                   suíte pytest com banco temporário
├── curl/                     coleção de requisições
├── docs/                     documentação e análise
├── seed.py                   dados de teste
└── requirements.txt
```

O log estruturado é gravado em `logs/api.jsonl`, uma linha JSON por requisição:

```json
{"instante": "2026-09-03T20:26:29.014+00:00", "correlacao": "3e218cc84582", "metodo": "POST", "caminho": "/v1/livros", "consulta": null, "status": 201, "duracao_ms": 12.84, "cliente": "127.0.0.1"}
```

O campo `correlacao` é o mesmo valor devolvido no cabeçalho `X-Request-ID` e presente no corpo
de qualquer erro, permitindo localizar a requisição exata a partir do relato do cliente.

---

## Requisitos da atividade

| Requisito | Onde é atendido |
| --- | --- |
| Duas coleções relacionadas | livros e empréstimos, com relação 1 para N |
| No mínimo seis endpoints | treze, cobrindo GET, POST, PUT, PATCH e DELETE |
| Validação de entrada | `app/esquemas.py`, com `extra="forbid"` e validadores próprios |
| Tratamento explícito de 404 e 409 | `app/erros.py`, cenários C03 e C04 |
| Cliente de teste com timeout | `cliente/comum.py`, `TIMEOUT = 3.0` em toda requisição |
| Persistência | SQLite com `sqlite3` puro, consultas parametrizadas |
| Dois erros de aplicação | 422, 404, 409 e 412 — quatro tipos, cenários C02 a C06 |
| Uma falha de conectividade | `ConnectionError` no cenário C08 |
| Logs coletados | `logs/api.jsonl`, uma linha JSON por requisição |
| Tabela de evidências | [`docs/04-evidencias.md`](docs/04-evidencias.md), gerada automaticamente |
| Questões de análise | [`docs/05-questoes-de-analise.md`](docs/05-questoes-de-analise.md) |

Desafios opcionais implementados: `ETag` com versionamento otimista e validação condicional
(`304`, `412`), e paginação com filtros e limite máximo. Não implementados: autenticação por
token e execução de clientes concorrentes em paralelo — o conflito entre dois clientes é
demonstrado de forma sequencial e determinística no cenário C06.

---

## Roteiro de demonstração

```powershell
python seed.py
.\.venv\Scripts\fastapi.exe dev app\main.py
```

Em outro terminal:

```powershell
curl.exe -i http://127.0.0.1:8000/v1/livros/1
.\.venv\Scripts\python.exe -m cliente.executar_todos
.\.venv\Scripts\python.exe -m pytest
Get-Content logs\api.jsonl -Tail 5
```

1. `/docs` mostra o contrato gerado a partir do código
2. `curl.exe -i` na leitura de um livro exibe o `ETag`
3. os cenários exibem os 44 resultados e regravam a tabela de evidências
4. o `pytest` confirma as invariantes de contrato
5. o log mostra método, caminho, status, duração e correlação de cada requisição

---

## Decisões de projeto

**SQLite com `sqlite3` puro, sem ORM.** Um ORM esconderia exatamente o que a atividade quer
mostrar: a tradução entre o modelo de recursos da API e o modelo relacional do banco. Com SQL
parametrizado à vista, fica explícito onde a restrição de unicidade do ISBN vira um `409` e
onde a chave estrangeira vira um `404`.

**Camada de repositório separada das rotas.** As rotas traduzem HTTP para domínio e vice-versa;
os repositórios não sabem que existe HTTP. Por isso um erro de domínio como "livro sem exemplar
disponível" é levantado sem escolher código de status — a escolha acontece em um único lugar,
em `app/erros.py`. É a mesma separação que a AP4 repete com os interceptors.

**Esquemas de entrada e saída separados, com `extra="forbid"`.** Um campo desconhecido no corpo
é recusado com `422` em vez de ignorado em silêncio. Ignorar seria pior: o cliente acharia que
enviou algo que o servidor nunca leu — e descobriria em produção.

**`application/problem+json` em vez de um envelope próprio.** O formato é padronizado (RFC 9457)
e evita a decisão arbitrária de como nomear os campos de erro. Todo erro carrega o mesmo
identificador de correlação que aparece no log, então o relato de um cliente localiza a
requisição exata.

**Versão no caminho (`/v1/...`).** É a forma mais visível de versionar, e deixa explícito que o
contrato pode mudar. A AP4 faz o mesmo no nome do pacote `.proto`, pelo mesmo motivo.

**Rotas de diagnóstico separadas do domínio.** `/v1/lento` e `/v1/indisponivel` existem porque
demonstrar timeout e indisponibilidade **de propósito** é mais confiável do que esperar uma
falha acontecer. É a mesma ideia dos controles de laboratório do servidor da AP4.

---

## Aprendizados

**Idempotência é propriedade do estado final, não da resposta.** Foi o ponto que mais mudou de
forma ao ser testado. `DELETE` de um livro devolve `204` na primeira chamada e `404` na segunda
— respostas diferentes, e ainda assim a operação é idempotente, porque o estado do servidor é o
mesmo nos dois casos. Confundir "mesma resposta" com "mesmo efeito" leva a clientes que tratam
o segundo `404` como erro quando ele é, na verdade, confirmação.

**Nem todo conflito é o mesmo conflito.** `409` e `412` parecem intercambiáveis até você
precisar de cada um. O `409` diz que o pedido contradiz o estado atual (emprestar um livro sem
exemplar livre). O `412` diz que o pedido foi feito sobre uma versão que não é mais a atual
(alterar um livro com um `ETag` velho). O primeiro é sobre o **quê**, o segundo é sobre
**quando** — e o cliente reage diferente: no primeiro corrige o pedido, no segundo relê o
recurso e tenta de novo.

**A perda de atualização é invisível sem versionamento.** No cenário C06, dois clientes leem o
mesmo livro, os dois editam, e sem `If-Match` o segundo `PUT` sobrescreve o primeiro sem que
ninguém perceba. Com `ETag`, o segundo recebe `412` e fica sabendo. O mecanismo custa um
cabeçalho e evita uma classe inteira de bug silencioso.

**"O servidor respondeu erro" e "não obtive resposta" são coisas diferentes.** É a distinção do
cenário C08, e é a mais importante da atividade. Um `503` é uma resposta: o servidor recebeu,
decidiu e respondeu — a operação certamente não aconteceu. Um `ConnectionError` não é resposta
nenhuma: o cliente não sabe se o pedido chegou, se foi executado, ou se só a resposta se
perdeu. Essa dúvida reaparece medida na [AP4](../Atividade-Pratica-4/README.MD), onde um
cliente registrou `DEADLINE_EXCEEDED` para uma chamada que o servidor concluiu com sucesso.

**HTTP tem mais vocabulário do que normalmente se usa.** A maior parte das APIs vive com `200`,
`404` e `500`. Modelar de propósito o `304`, o `412` e o `Retry-After` mostra que boa parte do
que se costuma implementar na mão — cache, controle de concorrência, sinalização de retry — já
está especificada e só precisa ser usada.

---

## Ponte para as atividades seguintes

A AP2 resolve o que a AP1 deixou em aberto, e deixa as suas próprias perguntas:

| Limite da AP2 | Consequência | Explorado em |
| --- | --- | --- |
| O cliente precisa saber quem chamar | acoplamento à URL do servidor | [AP3](../Atividade-Pratica-3/README.MD) — o broker desacopla quem publica de quem consome |
| Um pedido, um destinatário | notificar três serviços exige três chamadas | AP3 — um `publish`, N assinantes |
| O cliente espera a resposta | acoplamento temporal: os dois precisam estar no ar | AP3 — entrega assíncrona com QoS |
| O contrato é documentação | quebrar o formato só aparece em execução | [AP4](../Atividade-Pratica-4/README.MD) — `.proto` compilado nas duas pontas |
| JSON é verboso e sem tipo garantido | validação em tempo de execução, a cada requisição | AP4 — Protocol Buffers, tipos verificados na geração |

