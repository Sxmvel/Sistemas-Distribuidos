# AP9 — Testes, observabilidade e medição

Laboratório da Atividade Prática 9 de Sistemas Distribuídos, sobre o capítulo 16 do material
(*Testes, Observabilidade e Medição em Sistemas Distribuídos*), com as respostas aos exercícios de
fixação do capítulo 15 em `entregavel/Questoes-AP9.docx`.

O ponto de partida é a frase da seção 16.1: *sistemas distribuídos falham nas fronteiras*. Por isso
o sistema sob teste tem fronteiras de verdade: três processos HTTP no domínio da biblioteca das
atividades anteriores, um gateway com failover na frente de duas réplicas, logs estruturados com
correlação entre os três e um proxy de falhas que perturba o canal sem os serviços saberem. Sobre
ele rodam sete experimentos, cada um com pergunta, hipótese, procedimento e verificações numéricas.

---

## Arquitetura

```text
 gerador de carga ──▶ balcão :8100 ──┬──▶ [proxy :8301] ──▶ acervo-a :8201
 (N clientes,         rodízio,        │
  malha fechada)      failover,       └──▶ [proxy :8302] ──▶ acervo-b :8202
                      quarentena            (só no E07)      fila, lentidão e erro injetáveis

 cada processo ──▶ logs/<experimento>/<processo>.jsonl ──▶ medicao/traces.py (árvore por correlation_id)
```

| Pasta | Conteúdo |
| --- | --- |
| [`servicos/`](servicos) | `acervo.py` (réplica com fila explícita e falhas injetáveis), `balcao.py` (gateway com failover, quarentena e fan-out), configuração por variável de ambiente, catálogo sintético |
| [`observabilidade/`](observabilidade) | contexto propagado por cabeçalho, log JSON com os campos da seção 16.8, middleware que registra o span de servidor |
| [`medicao/`](medicao) | gerador de carga com classificação de erro, estatística (percentis, vazão, disponibilidade), reconstrução de traces e o `medir_latencia.py` do material |
| [`laboratorio/`](laboratorio) | orquestração de processos, proxy TCP de falhas, os experimentos E01–E07 e o gerador do relatório |
| [`testes/`](testes) | 65 testes funcionais com `pytest`, sem rede |

O que é entregue fica em `entregavel/`, separado do código-fonte. A pasta é gerada localmente (os experimentos gravam nela) e fica fora do repositório, no `.gitignore`:

| Arquivo | Conteúdo |
| --- | --- |
| `Questoes-AP9.docx` | respostas aos exercícios de fixação do capítulo 15, objetivos do capítulo 16 com as medições, e questões do guia de estudos respondidas pelos experimentos |
| `docs/01-plano-experimental.md` | métricas, instrumentação, procedimento, hipóteses e limites da medição |
| `docs/02-evidencias.md` | relatório gerado pelos experimentos: tabelas, traces e as 60 verificações |
| `docs/03-mapa-dos-conceitos.md` | cada seção do material e onde ela aparece no código |
| `evidencias/` | um JSON por experimento, com os dados brutos dos resumos, verificações e ambiente |

---

## Execução

Requisitos: Python 3.12 ou mais novo (testado com 3.14.3, Windows 11). Portas 8100, 8201, 8202,
8301 e 8302 livres. Não há Docker nem banco de dados.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Testes funcionais

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Todos os experimentos

```powershell
.\.venv\Scripts\python.exe -m laboratorio.executar_todos
```

Leva cerca de 3 minutos. Apaga as evidências antigas, roda E01 a E07 em sequência, grava
`entregavel/evidencias/e0N.json` e regenera `entregavel/docs/02-evidencias.md`. Sai com código
1 se alguma verificação falhar. Um experimento isolado (`python -m laboratorio.e04_carga_e_saturacao`)
atualiza só o JSON dele e regenera o relatório com todos os que existirem.

### Explorar à mão

```powershell
$env:AP9_LOG = "logs/manual/acervo-a.jsonl"; $env:ACERVO_INSTANCIA = "acervo-a"
.\.venv\Scripts\python.exe -m uvicorn servicos.acervo:criar_app --factory --port 8201
```

```powershell
$env:AP9_LOG = "logs/manual/balcao.jsonl"; $env:BALCAO_REPLICAS = "http://127.0.0.1:8201"
.\.venv\Scripts\python.exe -m uvicorn servicos.balcao:criar_app --factory --port 8100
```

```powershell
.\.venv\Scripts\python.exe -m medicao.carga http://127.0.0.1:8100/v1/livros/1 --concorrencia 4 --total 500 --aquecimento 20 --slo-ms 100
.\.venv\Scripts\python.exe -m medicao.medir_latencia http://127.0.0.1:8100/v1/livros/1
.\.venv\Scripts\python.exe -m medicao.traces logs/manual/balcao.jsonl logs/manual/acervo-a.jsonl --limite 2
```

Variáveis do acervo: `ACERVO_TRABALHADORES`, `ACERVO_TEMPO_SERVICO_MS`, `ACERVO_PROB_LENTIDAO`,
`ACERVO_ATRASO_LENTO_MS`, `ACERVO_PROB_ERRO`, `ACERVO_SEMENTE`. Do balcão: `BALCAO_REPLICAS`,
`BALCAO_TIMEOUT_MS`, `BALCAO_TIMEOUT_CONEXAO_MS`, `BALCAO_QUARENTENA_S`. As duas leem `AP9_LOG`.

---

## Resultados

Última execução: **60 de 60 verificações aprovadas** (detalhes, tabelas e traces em
`entregavel/docs/02-evidencias.md`).

| | Experimento | Pergunta | Resultado principal |
| --- | --- | --- | --- |
| E01 | Referência, aquecimento e repetibilidade | Como é o regime normal, e a medição se repete? | p50 de 19,7–19,8 ms em 3 execuções com processos novos (dispersão 0,5%). O `medir_latencia.py` do material mede 43,9 ms no mesmo endpoint, porque abre uma conexão por chamada; com `Session`, 19,8 ms |
| E02 | Média contra percentis | Uma média boa garante bom atendimento? | 2,6% de requisições com +500 ms: média 32,2 ms (abaixo do objetivo de 100 ms), p95 24,6 ms, p99 **521,4 ms** |
| E03 | Amplificação da cauda | Quanto a cauda cresce com o número de dependências? | mesma réplica, lenta em 2% das chamadas: 2,4% de operações lentas com 1 chamada, 7,6% com 5, 17,0% com 10 (previsto 2,0%, 9,6% e 18,3%) |
| E04 | Carga, vazão e saturação | Onde a vazão para, e onde está o gargalo? | pico de 187,8 req/s com 8 clientes (98% da capacidade teórica); lei de Little dentro de 3% em todos os níveis; com 32 clientes a vazão **cai** para 134,7 req/s e o gargalo migra do acervo para o balcão (96% de CPU, 179,5 ms na chamada contra 23,3 ms de atendimento) |
| E05 | Correlação e trace distribuído | Dá para ligar o erro interno à requisição externa? | 60/60 operações reconstruídas dos logs de 3 processos, 0 spans órfãos; os 12 erros 500 da réplica A, invisíveis para o cliente, aparecem como 12 mensagens entregues às duas réplicas |
| E06 | Caos: queda de réplica | O estado estável sobrevive a um `kill` sob carga? | sim: 0 erros em 3.267 requisições e disponibilidade de 100% nas três fases; o balcão tentou a réplica morta só 10 vezes graças à quarentena: 2 requisições interrompidas pelo `kill` e duas rajadas de 4 (o número de clientes) quando a quarentena expirou |
| E07 | Caos: classes de erro | A mesma indisponibilidade chega igual ao cliente? | não: sucesso com p99 de ~276 ms (réplica lenta ou muda), HTTP 504 (acervo mudo), HTTP 503 (acervo morto), conexão recusada após ~2 s (balcão morto) |

O que a atividade mostra, em três frases:

* **A média e a latência do cliente escondem onde está o problema.** O p99 mostrou a cauda que a
  média diluiu (E02), e só a decomposição por spans com a CPU por processo mostrou que o gargalo tinha
  mudado de lugar (E04).
* **Sem correlação, o failover apaga a evidência.** O cliente viu 0% de erro enquanto uma réplica
  falhava em 12 de 30 atendimentos (E05), e o timeout descartou respostas que o acervo tinha produzido (E07).
* **Erro de aplicação e erro de transporte são informações diferentes.** Um diz que a borda está viva e
  a dependência falhou; o outro diz que nem a borda respondeu (E07). O script do material soma os dois.

---

## Decisões e limites

* **Rede de verdade, mesma máquina.** Os serviços são processos separados falando HTTP pelo
  loopback, então as fronteiras existem. Mas o gerador disputa CPU com eles, e o E04 mostra isso
  medindo a CPU de cada processo.
* **Malha fechada.** A concorrência é o controle e a vazão é o resultado, o que torna a lei de
  Little verificável. O custo é subestimar travamentos globais (*coordinated omission*), discutido
  no plano experimental (`entregavel/docs/01-plano-experimental.md`, seção 6).
* **Relógio de 1 ms no Windows.** Sem `timeBeginPeriod(1)`, todo `asyncio.sleep` arredonda para
  ~15,6 ms e a latência anda em degraus. Os serviços ativam o relógio fino no início e registram isso no log.
* **Tracing feito à mão.** Quatro cabeçalhos e um campo `parent_span_id` bastam para reconstruir a
  árvore, sem OpenTelemetry. É a ideia essencial da seção 16.9, com tudo visível no código.
* **Só leituras.** As réplicas servem um catálogo fixo, então o failover é sempre seguro. Os
  `message_id` repetidos que os experimentos detectam seriam, numa escrita, o sinal de que o acervo
  precisa deduplicar, que é o problema da AP5.
