# Roteiro reproduzível

Todos os comandos partem da pasta `Atividade-Pratica-4` e usam o interpretador do ambiente
virtual pelo caminho explícito, que funciona mesmo sem ativar o `.venv`.

## 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não há Docker, broker nem banco de dados: o serviço guarda o estado em memória e cada
experimento sobe o seu próprio servidor em uma porta livre.

## 2. Regenerar os stubs do zero

```powershell
.\.venv\Scripts\python.exe gerar_stubs.py
```

Saída esperada:

```text
contratos: removidos 3 -> gerados emprestimos_pb2.py, emprestimos_pb2.pyi, emprestimos_pb2_grpc.py
contratos_legado: removidos 3 -> gerados emprestimos_pb2.py, emprestimos_pb2.pyi, emprestimos_pb2_grpc.py
contratos_incompativel: removidos 2 -> gerados emprestimos_pb2.py, emprestimos_pb2.pyi
```

O script apaga os arquivos gerados antes de chamar o `protoc`, então ele é seguro de rodar a
qualquer momento. Na primeira execução em um clone limpo, `removidos` é 0.

## 3. Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest
```

58 testes, cerca de 5 s. Cobrem contrato, serviço, os cinco status de erro, deadline,
cancelamento, streaming, servidor indisponível e concorrência. Sobem o servidor em porta
efêmera dentro do próprio processo de teste, sem depender de nada externo.

## 4. Experimentos

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos
```

Cerca de 28 s. Roda os sete cenários, imprime cada verificação e grava
[`docs/04-evidencias.md`](04-evidencias.md) com a tabela de latência/status e a tabela de
verificações. Para rodar só alguns:

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos E03 E06
```

| Cenário | O que demonstra | Como |
| --- | --- | --- |
| E01 | contrato, stubs regeneráveis, unary e streaming | compara SHA-256 dos gerados; faz o ciclo empréstimo → consulta → listagem → devolução |
| E02 | erros de domínio contra status gRPC | oito entradas inválidas, conflito de estado, chave duplicada e servidor desligado |
| E03 | deadlines de 100 ms, 1 s e 3 s | mesma chamada de ~1,2 s com três orçamentos de tempo |
| E04 | indisponibilidade | derruba e religa o servidor com o cliente conectado; mata o processo no meio de uma chamada |
| E05 | concorrência | 8 clientes × 3 chamadas com `max_workers` 2 e 16; 12 clientes disputando 1 exemplar |
| E06 | retry e idempotência | escrita lenta + deadline curto, com e sem chave de idempotência |
| E07 | evolução de contrato | cliente legado em subprocesso; leitura dos bytes v2 com esquema incompatível |

## 5. Execução manual, para a demonstração

Terminal 1 — servidor:

```powershell
.\.venv\Scripts\python.exe -m app.servidor --porta 50051 --workers 8 --semear 4
```

Terminal 2 — cliente:

```powershell
.\.venv\Scripts\python.exe -m app.cliente --porta 50051
```

O cliente executa sete chamadas e imprime status, latência e a política de retry sugerida:

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

A primeira chamada custa ~270 ms e as seguintes ~2 ms: o canal é aberto de forma preguiçosa,
e o custo de estabelecer a conexão HTTP/2 aparece inteiro na primeira RPC. Nas chamadas
seguintes a mesma conexão é reaproveitada.

Para demonstrar indisponibilidade ao vivo, encerre o terminal 1 com `Ctrl+C` e rode o cliente
de novo: as mesmas chamadas passam a devolver `UNAVAILABLE`.

### Opções do servidor

| Opção | Uso |
| --- | --- |
| `--porta` | porta de escuta (`0` escolhe uma livre) |
| `--workers` | tamanho do `ThreadPoolExecutor`; usado no E05 |
| `--semear N` | cria N empréstimos no início, para ter `EMP-0001`… disponíveis |
| `--custo-por-codigo S` | segundos gastos por item em `CalcularMultas`; controla o E03 |
| `--atraso-na-escrita S` | segundos entre gravar e responder em `RegistrarEmprestimo`; cria a janela ambígua do E06 |
| `--silencioso` | não imprime os eventos no console (continua gravando o `.jsonl`) |

As duas últimas são instrumentos de laboratório, não comportamento de produção. Elas existem
para tornar deadline e ambiguidade **determinísticos** em vez de depender de sorte de
temporização.

### Opções do cliente

| Opção | Uso |
| --- | --- |
| `--host`, `--porta` | endereço do servidor |
| `--deadline-curto` | deadline da chamada que deve estourar (padrão 0,3 s) |
| `--deadline-longo` | deadline das chamadas que devem concluir (padrão 3 s) |

## 6. Logs

Cada processo grava uma linha JSON por evento:

```text
logs/<id>.jsonl        eventos estruturados
logs/<id>.saida.txt    stdout/stderr do processo
```

Eventos do servidor: `servidor-no-ar`, `chamada-recebida` (com `prazo_restante_s`),
`chamada-concluida` (com `metodo`, `status`, `latencia_ms`, `correlacao`) e `resumo`.
Eventos do cliente: `resposta-recebida` e `fluxo-aberto`, com o mesmo `correlacao`.

Para seguir uma chamada das duas pontas:

```powershell
Select-String -Path logs\*.jsonl -Pattern '<id-de-correlacao>'
```

## 7. Checklist da AP4

| Item | Onde verificar |
| --- | --- |
| O `.proto` pode ser regenerado do zero | `gerar_stubs.py`; E01 confirma por hash |
| O cliente define deadline | `app/cliente.py`, parâmetro `timeout` em toda chamada |
| Existem testes de erro e servidor indisponível | `testes/test_erros.py`, `testes/test_resiliencia.py` |
| Há experimento concorrente | E05 e `test_disputa_pelo_unico_exemplar_aceita_apenas_um` |
| Foi feita mudança compatível no contrato | `contratos_legado/` e E07 |
