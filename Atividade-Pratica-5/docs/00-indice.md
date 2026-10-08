# Documentação da AP5

Experimentos com interação, falhas e segurança sobre a API REST de biblioteca da AP2.

| Documento | Conteúdo |
| --- | --- |
| [01 — Fundamentos](01-fundamentos.md) | Modelos de interação e de falhas, timeout como detector imperfeito, retry, backoff, jitter, circuit breaker, idempotência e canais seguros. |
| [02 — Plano experimental](02-plano-experimental.md) | Hipótese, mecanismo de injeção, métrica e critério de cada cenário; como observação e inferência são separadas. |
| [03 — Roteiro reproduzível](03-roteiro-reproduzivel.md) | Passo a passo para instalar, testar, reproduzir cada experimento e fazer a demonstração. |
| [04 — Evidências](04-evidencias.md) | Tabela de classificação, métricas por tentativa e verificações. **Gerado automaticamente.** |
| [05 — Análise de segurança](05-analise-de-seguranca.md) | Modelo de ameaças simplificado, controle aplicado, evidência e ameaças residuais. |
| [06 — Glossário](06-glossario.md) | Termos usados no código e nos documentos. |

## Onde cada requisito da AP5 está atendido

| Requisito obrigatório | Onde | Evidência |
| --- | --- | --- |
| Pelo menos quatro cenários de falha distintos | [`experimentos/`](../experimentos/) | E02 a E09: atraso, erro de aplicação, indisponibilidade, crash, perda de requisição, perda de resposta, latência de rede, retry não idempotente, tempestade de retries, falha dupla |
| Duração, resultado e tipo de erro por tentativa | [`cliente/resiliencia.py`](../cliente/resiliencia.py) | seção "Tentativas individuais" de [04](04-evidencias.md) e `logs/tentativas.csv` |
| Cenário com retry limitado e backoff | [`experimentos/e03_erro_e_retry.py`](../experimentos/e03_erro_e_retry.py) | E03 — até 4 tentativas, espera de 0,2 × 2ⁿ s + jitter de até 0,1 s |
| Efeito adverso de retry ou operação não idempotente | [`experimentos/e06_retry_nao_idempotente.py`](../experimentos/e06_retry_nao_idempotente.py) | E06 — 3 empréstimos para 1 intenção; também E02 (carga ×4) e E07 (pico de tráfego) |
| Controle de segurança aplicável ao laboratório | [`app/seguranca.py`](../app/seguranca.py) | E10 — token Bearer, autorização por papel e validação robusta |

| Entregável | Onde |
| --- | --- |
| Código/configuração de injeção de falhas | [`app/falhas.py`](../app/falhas.py), [`app/rotas/experimento.py`](../app/rotas/experimento.py), [`experimentos/proxy.py`](../experimentos/proxy.py), [`experimentos/comum.py`](../experimentos/comum.py) |
| Tabela com hipótese, falha, observação, classificação e conclusão | [04 — Evidências](04-evidencias.md), seção "Tabela de classificação" |
| Logs ou métricas | `logs/*.jsonl` (servidor), `logs/tentativas.csv` (cliente), métricas e percentis em [04](04-evidencias.md) |
| Breve análise de segurança | [05 — Análise de segurança](05-analise-de-seguranca.md) |
| Demonstração de um cenário selecionado | [03 — Roteiro](03-roteiro-reproduzivel.md#6-demonstração) |

| Item do checklist | Como é atendido |
| --- | --- |
| Existe cenário de referência | E01, sem falha, com percentis de latência |
| As falhas são reproduzíveis | cada cenário sobe o próprio servidor; a falha probabilística usa semente fixa; duas execuções seguidas deram o mesmo resultado |
| Cada cenário possui evidência | tabela de verificações por cenário em [04](04-evidencias.md) e logs JSONL por servidor |
| Retries possuem limite e backoff | `chamar_com_retry` tem `tentativas` e espera exponencial com teto; verificado em E03 e nos testes |
| A análise distingue observação de inferência | colunas separadas na tabela de classificação; ver [02](02-plano-experimental.md#observação-e-inferência) |

| Desafio opcional | Onde |
| --- | --- |
| Toxiproxy ou ferramenta equivalente | [`experimentos/proxy.py`](../experimentos/proxy.py), usado em E05, E09 e E10 |
| Métricas de percentis de latência | p50, p95 e p99 em E01; p50 e p95 por cenário em [04](04-evidencias.md) |
| Circuit breaker simples | `Disjuntor` em [`cliente/resiliencia.py`](../cliente/resiliencia.py), exercitado em E08 |
