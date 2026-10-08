# AP5 — Experimentos com interação, falhas e segurança

Laboratório de falhas controladas da Atividade Prática 5 de Sistemas Distribuídos. O sistema
submetido às falhas é a **API REST de biblioteca da AP2**, copiada para esta pasta e estendida —
o enunciado pede uma rota experimental no servidor REST, e manter o mesmo domínio das atividades
anteriores faz o experimento ser sobre o modelo de falhas, e não sobre o problema.

A atividade injeta atraso, erro, indisponibilidade, crash, perda de mensagem no canal e falhas
simultâneas; mede duração, resultado e tipo de erro de cada tentativa; compara retry com e sem
backoff; mostra o efeito adverso do retry numa operação não idempotente; e aplica um controle de
segurança (token Bearer com autorização por papel e validação robusta).

---

## Execução

### 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não há Docker nem broker. Os experimentos sobem os próprios servidores (uvicorn em
subprocesso), cada um com banco SQLite e log isolados em `logs/`.

### 2. Servidor

```powershell
$env:BIBLIOTECA_LABORATORIO = "1"
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

`BIBLIOTECA_LABORATORIO=1` liga a rota `/experimento/instavel`. Sem ela, a rota responde 404:
endpoint de injeção de falha não existe fora do laboratório.

### 3. Demonstração ao vivo

Em outro terminal, com o servidor acima no ar:

```powershell
.\.venv\Scripts\python.exe -m cliente.demonstracao --prob-falha 0.5 --chamadas 5
.\.venv\Scripts\python.exe -m cliente.demonstracao --atraso-ms 800 --prob-falha 0 --chamadas 2
```

Cada tentativa aparece com duração, status e tipo de erro, e cada retry com a espera do backoff:

```text
chamada 3 - GET http://127.0.0.1:8000/experimento/instavel {'atraso_ms': 0, 'prob_falha': 0.5} timeout=0.5s
falha erro-de-aplicacao; retry em 0.23s
falha erro-de-aplicacao; retry em 0.47s
  tentativa 1:     5.7 ms  status=503  tipo=erro-de-aplicacao
  tentativa 2:     5.4 ms  status=503  tipo=erro-de-aplicacao
  tentativa 3:     8.1 ms  status=200  tipo=sucesso
  resultado final: sucesso em 712 ms

chamada 1 - GET http://127.0.0.1:8000/experimento/instavel {'atraso_ms': 800, 'prob_falha': 0.0} timeout=0.5s
falha timeout-de-leitura; retry em 0.29s
falha timeout-de-leitura; retry em 0.44s
falha timeout-de-leitura; retry em 0.86s
  tentativa 1:   518.6 ms  status=-    tipo=timeout-de-leitura
  tentativa 2:   528.7 ms  status=-    tipo=timeout-de-leitura
  tentativa 3:   506.5 ms  status=-    tipo=timeout-de-leitura
  tentativa 4:   515.6 ms  status=-    tipo=timeout-de-leitura
  resultado final: falha em 3666 ms
```

O primeiro caso é uma falha transitória que o retry resolve; o segundo é um atraso persistente
em que o retry só multiplica o trabalho do servidor.

---

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest
```

81 testes em cerca de 4 s: os 45 herdados da AP2 e 36 novos para autenticação e autorização,
chave de idempotência, rota de laboratório e a política de retry, backoff e circuit breaker do
cliente.

## Experimentos

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos
```

Cerca de 75 s. Roda os dez cenários, grava [`docs/04-evidencias.md`](docs/04-evidencias.md) com a
tabela de hipótese, falha, observação, classificação e conclusão, e grava `logs/tentativas.csv`
com cada tentativa medida. Para rodar apenas alguns: `... -m experimentos.executar_todos E05 E06`.

| Cenário | Falha | Resultado principal |
| --- | --- | --- |
| E01 | nenhuma (referência) | 40/40 com 200; p95 ≈ 30 ms, cerca de 17× abaixo do timeout |
| E02 | atraso de 800 ms no servidor | cliente vê timeout, servidor registra 200; retry quadruplica a carga sem ganho |
| E03 | 503 com probabilidade 0,5 | retry com backoff sobe o sucesso de 45% para 95% |
| E04 | servidor fora, religado, morto no meio | recusa aparece como timeout com prazo curto; retry recupera depois de 2 ou 3 tentativas sem conexão |
| E05 | proxy perde requisição, perde resposta, atrasa | quatro causas, mesma observação: timeout de leitura aos ~520 ms |
| E06 | escrita lenta + retry | sem chave, 3 empréstimos para 1 intenção; com `Idempotency-Key`, 1 |
| E07 | 20 clientes, 60% de falha | retry imediato: quase todas as 40 requisições na mesma janela de 100 ms; backoff com jitter: 20 |
| E08 | dependência fora do ar | circuit breaker corta de 12 para 3 tentativas na rede |
| E09 | duas réplicas falhando juntas | failover mascara uma falha, não duas |
| E10 | ataques ao controle de acesso | 401, 403 e 422 corretos; token capturado em texto claro sem TLS |

Quatro execuções completas: **69 verificações, 0 falhas** em todas (261 a 262 tentativas medidas).

---

## Estrutura

```text
app/                     API REST da AP2, estendida
  config.py              parâmetros por variável de ambiente (banco, log, tokens, laboratório)
  falhas.py              atraso de escrita, sorteio de falha com semente, trava do laboratório
  seguranca.py           token Bearer e autorização por papel
  rotas/experimento.py   GET /experimento/instavel (atraso e falha injetados)
  repositorios/emprestimos.py  Idempotency-Key gravada na mesma transação do empréstimo
  observabilidade.py     log JSONL com correlação e número da tentativa

cliente/
  resiliencia.py         tentativa medida e classificada, retry com backoff e jitter,
                         failover entre réplicas, circuit breaker, get_com_retry do enunciado
  demonstracao.py        cliente de linha de comando para a demonstração

experimentos/
  comum.py               orquestração dos servidores, coletor de evidências, percentis
  proxy.py               proxy TCP de falhas (perde requisição, perde resposta, atrasa, escuta)
  e01 ... e10            dez cenários
  executar_todos.py      orquestrador e gerador do relatório

testes/                  81 testes com pytest
docs/                    documentação e evidências geradas
```

### Decisões de projeto

**Cópia da AP2, não alteração.** A AP2 é uma entrega fechada. A AP5 parte de uma cópia dela e
acrescenta apenas o que o laboratório exige, então a diferença entre as duas pastas é exatamente
o código de injeção de falhas, resiliência e segurança.

**Falhas injetadas em três lugares.** No servidor (rota instável e atraso depois da escrita),
no canal (proxy TCP entre cliente e servidor) e no processo (encerrar, religar e matar o
uvicorn). Cada lugar produz uma classe diferente de falha do modelo fundamental, e o proxy é o
único jeito de perder uma mensagem sem que nenhum dos dois lados saiba.

**Correlação em todas as tentativas.** O cliente envia o mesmo `X-Request-ID` em todas as
tentativas de uma chamada e o número da tentativa em `X-Tentativa`. É isso que permite
comparar o que o cliente viu com o que o servidor fez — a diferença entre observação e
inferência que o enunciado pede.

**Rota de laboratório desligada por padrão.** `BIBLIOTECA_LABORATORIO` vale `0` se não for
definida, e os parâmetros da rota têm limites (`atraso_ms` até 10 s, `prob_falha` entre 0 e 1).
Sem esse limite, a própria ferramenta de teste seria um vetor de negação de serviço.

---

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [00 — Índice](docs/00-indice.md) | mapa dos documentos e onde cada requisito da AP5 é atendido |
| [01 — Fundamentos](docs/01-fundamentos.md) | modelos de interação e de falhas, timeout, retry, backoff, circuit breaker, idempotência |
| [02 — Plano experimental](docs/02-plano-experimental.md) | hipóteses, mecanismos de injeção, métricas e critérios de cada cenário |
| [03 — Roteiro reproduzível](docs/03-roteiro-reproduzivel.md) | passo a passo de execução e da demonstração |
| [04 — Evidências](docs/04-evidencias.md) | tabelas geradas pela execução dos experimentos |
| [05 — Análise de segurança](docs/05-analise-de-seguranca.md) | modelo de ameaças, controle aplicado e ameaças residuais |
| [06 — Glossário](docs/06-glossario.md) | termos usados no código e nos documentos |
