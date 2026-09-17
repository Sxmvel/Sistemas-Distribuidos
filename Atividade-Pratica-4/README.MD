# AP4 — Serviço remoto de empréstimos com gRPC

Serviço gRPC construído com Protocol Buffers para a Atividade Prática 4 de Sistemas
Distribuídos. O domínio é o mesmo das atividades anteriores — o acervo de uma biblioteca —
para que a comparação entre REST (AP2), MQTT (AP3) e gRPC (AP4) seja sobre o estilo de
comunicação, e não sobre o problema.

A atividade demonstra contrato em IDL, geração reproduzível de stubs, tradução de erros de
domínio para status gRPC, deadlines com cancelamento observado no servidor, comportamento sob
indisponibilidade, concorrência com pool de threads, retry seguro por idempotência e evolução
compatível de contrato.

---

## Execução

### 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não há Docker, broker nem banco de dados. Todos os comandos abaixo usam o interpretador do
`.venv` pelo caminho explícito, o que funciona sem ativar o ambiente.

### 2. Gerar os stubs

```powershell
.\.venv\Scripts\python.exe gerar_stubs.py
```

Regenera o código dos três contratos do zero, apagando os arquivos anteriores.

### 3. Servidor

```powershell
.\.venv\Scripts\python.exe -m app.servidor --porta 50051 --workers 8 --semear 4
```

### 4. Cliente

Em outro terminal:

```powershell
.\.venv\Scripts\python.exe -m app.cliente --porta 50051
```

Executa sete chamadas e imprime status, latência e política de retry sugerida:

```text
chamada                                        status                 latência
------------------------------------------------------------------------------------------------
RegistrarEmprestimo (válido)                   OK                     274.3 ms
RegistrarEmprestimo (retry, reaproveitado=True) OK                       1.9 ms
RegistrarEmprestimo (isbn inválido)            INVALID_ARGUMENT         1.5 ms — isbn: isbn deve ter exatamente 13 dígitos
ConsultarEmprestimo (inexistente)              NOT_FOUND                1.0 ms — codigo: empréstimo EMP-9999 não existe
ListarEmprestimos (stream, 5 itens)            OK                       2.7 ms
CalcularMultas (deadline 0.3s)                 DEADLINE_EXCEEDED      313.8 ms — Deadline Exceeded
                                               política sugerida: repetir apenas com chave de idempotência
CalcularMultas (deadline 3.0s)                 OK                    1220.6 ms
```

---

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest
```

58 testes em cerca de 5 s, cobrindo contrato, serviço, os cinco status de erro, deadline,
cancelamento, streaming, servidor indisponível e concorrência. Sobem o servidor em porta
efêmera dentro do processo de teste.

## Experimentos

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos
```

Cerca de 28 s. Roda os sete cenários e grava [`docs/04-evidencias.md`](docs/04-evidencias.md)
com a tabela de latência/status por chamada e a tabela de verificações. Para rodar apenas
alguns: `... -m experimentos.executar_todos E03 E06`.

| Cenário | O que demonstra | Resultado principal |
| --- | --- | --- |
| E01 | contrato, stubs regeneráveis, unary e streaming | stubs byte a byte idênticos ao regenerar; 5 métodos, 11 mensagens |
| E02 | erros de domínio contra status gRPC | 5 status distintos; deadline curto mascara `UNAVAILABLE` |
| E03 | deadlines de 100 ms, 1 s e 3 s | servidor abandona a chamada em 4 de 40 itens |
| E04 | indisponibilidade | mesmo pedido inválido devolve `INVALID_ARGUMENT` com o servidor no ar e `UNAVAILABLE` com ele fora |
| E05 | concorrência | p95 cai de ~1,2 s (2 workers) para ~0,3 s (16 workers); 12 clientes disputam 1 exemplar e só 1 vence |
| E06 | retry e idempotência | sem chave, o retry cria 2 empréstimos; com chave, 1 |
| E07 | evolução de contrato | cliente legado funciona contra o servidor novo; esquema incompatível corrompe em silêncio |

Última execução: **90 verificações, 0 falhas**, 37 medições de latência.

---

## Estrutura

```text
contratos/               contrato atual (v2) e stubs gerados
contratos_legado/        contrato anterior, sem o campo unidade
contratos_incompativel/  contra-exemplo com mudanças proibidas
gerar_stubs.py           regeneração reproduzível dos três

app/
  config.py              parâmetros do serviço e do laboratório
  acervo.py              livros, exemplares, leitores e unidades
  dominio.py             entidade, validações e erros de domínio
  repositorio.py         estado em memória com trava e idempotência
  servico.py             implementação dos cinco métodos RPC
  erros.py               erro de domínio -> status gRPC + política de retry
  interceptadores.py     correlação, métricas e tradução de erro
  servidor.py            servidor com CLI
  cliente.py             cliente com deadline, usado também pelos experimentos
  cliente_legado.py      cliente com os stubs do contrato anterior
  inspetor_incompativel.py  lê bytes v2 com o esquema incompatível
  registro.py            log estruturado em JSONL

experimentos/            sete cenários + orquestrador
testes/                  58 testes com pytest
docs/                    documentação e evidências geradas
logs/                    JSONL por processo (ignorado pelo git)
```

### Decisões de projeto

**Estado em memória.** O foco da AP4 é a chamada remota, não a persistência. O repositório
guarda os empréstimos em memória sob um `RLock`, o que mantém os experimentos determinísticos
e deixa a invariante de concorrência (nunca emprestar mais exemplares do que existem) visível
em um único lugar.

**Erros de domínio, não `context.abort` espalhado.** O serviço levanta `EntradaInvalida`,
`NaoEncontrado`, `PrecondicaoFalhou` e `JaExiste`; o interceptador do servidor traduz cada uma
para o status gRPC correspondente. O resultado é que `servico.py` não decide códigos de status
e a tradução mora em um lugar só.

**Três versões do contrato em pastas separadas.** Elas declaram o mesmo `package`, então o
descriptor pool do protobuf impede que coexistam no mesmo processo. Por isso o cliente legado
e o inspetor rodam como subprocessos — que é também como uma migração real acontece.

**Dois controles de laboratório no servidor.** `--custo-por-codigo` e `--atraso-na-escrita`
existem para tornar deadline e ambiguidade determinísticos em vez de depender de sorte de
temporização. Não são comportamento de produção, e estão documentados como tal.

---

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [00 — Índice](docs/00-indice.md) | mapa dos documentos e onde cada requisito da AP4 é atendido |
| [01 — Fundamentos de RPC](docs/01-fundamentos-rpc.md) | ilusão de chamada local, stubs, marshalling, deadlines, status, interceptors |
| [02 — Contrato e evolução](docs/02-contrato-e-evolucao.md) | o `.proto` campo a campo e o que é mudança compatível |
| [03 — Roteiro reproduzível](docs/03-roteiro-reproduzivel.md) | passo a passo de execução e opções de CLI |
| [04 — Evidências](docs/04-evidencias.md) | tabelas geradas pela execução dos experimentos |
| [05 — Questões de análise](docs/05-questoes-de-analise.md) | as cinco questões e a comparação com a AP2 e a AP3 |
| [06 — Glossário](docs/06-glossario.md) | termos usados no código e nos documentos |
