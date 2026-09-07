# AP2 — API REST de gerenciamento de acervo de biblioteca

API REST construída com FastAPI e SQLite para a Atividade Prática 2 de Sistemas Distribuídos.
O domínio é o acervo de uma biblioteca, escolhido por ser diferente do exemplo de dispositivos
e leituras da apostila.

A atividade demonstra modelagem de recursos, semântica HTTP, validação de entrada, tratamento
explícito de erros, concorrência otimista com `ETag`/`If-Match`, observabilidade com log
estruturado e testes de comportamento.

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
| 12 | GET | `/v1/lento`, `/v1/indisponivel` | 200, 503 | — |

Detalhamento de parâmetros, corpos e cabeçalhos em
[`docs/03-contrato-da-api.md`](docs/03-contrato-da-api.md).

---

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [00 - Índice](docs/00-indice.md) | mapa de cada conceito da apostila até o arquivo que o implementa |
| [01 - Fundamentos REST](docs/01-fundamentos-rest.md) | estilo arquitetural, interface uniforme, métodos e status |
| [02 - Modelagem](docs/02-modelagem-do-dominio.md) | recursos, relações e as decisões de esquema justificadas |
| [03 - Contrato](docs/03-contrato-da-api.md) | os doze endpoints em detalhe |
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
| No mínimo seis endpoints | doze, cobrindo GET, POST, PUT, PATCH e DELETE |
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
