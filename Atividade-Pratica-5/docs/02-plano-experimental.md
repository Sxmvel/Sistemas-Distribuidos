# Plano experimental

## Sistema sob teste

A API REST de biblioteca da AP2 (FastAPI + SQLite), executada pelo uvicorn em um subprocesso
por cenário. Cada servidor recebe por variável de ambiente o próprio banco, o próprio arquivo de
log, os tokens gerados para aquela execução e os controles de laboratório.

O cliente é [`cliente/resiliencia.py`](../cliente/resiliencia.py), usando `requests` com timeout
de 500 ms salvo indicação contrária.

## Como as falhas são injetadas

| Mecanismo | Onde | O que produz | Cenários |
| --- | --- | --- | --- |
| `GET /experimento/instavel?atraso_ms=` | servidor | processo lento | E02, E04, E05 |
| `GET /experimento/instavel?prob_falha=` | servidor | erro de aplicação 503, com semente fixa | E03, E07 |
| `BIBLIOTECA_ATRASO_NA_ESCRITA` | servidor | resposta lenta depois de o efeito já estar gravado | E06 |
| encerrar o uvicorn (`CTRL_BREAK`) | processo | indisponibilidade, conexão recusada | E04, E08, E09 |
| matar o uvicorn (`kill`) | processo | crash no meio de uma requisição | E04 |
| proxy `perder-requisicao` | canal | requisição aceita e nunca encaminhada | E05 |
| proxy `perder-resposta` | canal | resposta produzida e nunca entregue | E05 |
| proxy `atraso` | canal | latência de rede na volta | E05, E09 |
| proxy em modo `normal` lendo os bytes | canal | escuta passiva do tráfego | E10 |

O proxy de [`experimentos/proxy.py`](../experimentos/proxy.py) é um intermediário TCP entre
cliente e servidor, no papel que o toxiproxy teria. Ele permite o caso que nenhum outro
mecanismo reproduz: a mensagem some e **nenhum** dos dois processos sabe disso.

## Métricas coletadas

Por **tentativa**, no cliente:

| Campo | Significado |
| --- | --- |
| `correlacao` | id da chamada lógica, repetido em todas as tentativas (`X-Request-ID`) |
| `tentativa` | número da tentativa (`X-Tentativa`) |
| `duracao_ms` | do envio até a resposta ou o erro |
| `status` | status HTTP, ou `sem resposta` |
| `tipo_de_erro` | `timeout-de-leitura`, `timeout-de-conexao`, `conexao-recusada`, `conexao-interrompida`, `erro-de-aplicacao`, `erro-do-cliente`, `circuito-aberto` |
| `espera_s` | espera do backoff antes da tentativa seguinte |

Por **requisição recebida**, no servidor (`logs/<servidor>.jsonl`): instante, correlação,
tentativa, método, caminho, consulta, status e duração interna.

Comparar as duas visões pela correlação é o que mostra, por exemplo, que o servidor concluiu com
200 uma chamada que o cliente registrou como timeout.

## Cenários

| Cenário | Hipótese | Variável manipulada | Critério |
| --- | --- | --- | --- |
| E01 referência | sem falha, tudo responde e a latência fica muito abaixo do timeout | nenhuma | 40/40 com 200; p95 < 500 ms; contagens iguais no cliente e no servidor |
| E02 atraso | atraso > timeout aparece como timeout, mas o servidor conclui; retry não ajuda | atraso de 300 e 800 ms; timeout de 0,5 e 1,5 s | timeout no cliente com 200 no servidor; 4 execuções no servidor para 4 timeouts |
| E03 erro e retry | retry com backoff aumenta o sucesso de ~50% para ~94% | prob_falha 0,5; com e sem retry | taxa com retry ≥ 85%; esperas na faixa do backoff; 4xx não repetido |
| E04 indisponibilidade | sem servidor não há status HTTP; retry recupera queda temporária; crash deixa efeito em aberto | servidor fora, religado, morto | categorias corretas; sucesso após falhas; nenhum registro da requisição interrompida |
| E05 timeout ambíguo | quatro causas dão a mesma observação no cliente | modo do proxy e atraso do servidor | timeout de leitura nos quatro; log do servidor diferente por causa |
| E06 retry não idempotente | retry duplica a escrita; a chave de idempotência impede | presença de `Idempotency-Key` | 3 empréstimos sem chave; 1 com chave; replay com o mesmo id |
| E07 tempestade | retry imediato concentra tráfego; backoff com jitter espalha | espera entre tentativas | pico imediato > nº de clientes; pico com backoff ≤ nº de clientes |
| E08 circuit breaker | disjuntor corta tentativas na rede e se recupera sozinho | presença do disjuntor | 3 tentativas na rede em vez de 12; ciclo de estados completo |
| E09 falha dupla | redundância mascara uma falha, não duas | quantas réplicas falham e como | sucesso na 2ª tentativa com uma fora; falha com as duas |
| E10 segurança | escritas exigem identidade e papel; token não protege o canal | credencial, papel e entrada | 401, 403, 201 e 422 conforme o caso; token capturado pelo proxy |

## Observação e inferência

O relatório separa as duas coisas de propósito:

- **Observação** é o que foi medido: status, categoria, duração, contagem de linhas no log do
  servidor. Na tabela de classificação, a coluna "Observação" só contém números e categorias
  medidos na execução.
- **Inferência** é o que se conclui a partir disso e do modelo: a classificação da falha e a
  conclusão sobre retry, timeout ou segurança.

Exemplo do E02. Observação: o cliente registrou `timeout-de-leitura` em 537 ms; o log do
servidor tem, para a mesma correlação, status 200 em 802 ms. Inferência: o servidor não falhou,
estava lento; a falha é de temporização em relação ao limite que o cliente assumiu.

Algumas conclusões **não** são observadas, e o texto diz isso. O E09 afirma que as réplicas
compartilham o banco e que uma falha nele derrubaria as duas: isso é inferência a partir da
arquitetura, não um resultado medido.

## Reprodutibilidade

- cada cenário sobe servidores novos, em portas livres, com banco e log próprios;
- a pasta `logs/` é apagada no início de cada execução;
- a falha probabilística usa `random.Random` com semente fixa por cenário, então a sequência de
  falhas é a mesma enquanto a ordem das requisições for a mesma (E03 deu 45% → 95% em execuções
  consecutivas);
- os tokens são gerados a cada execução, então nenhum segredo fica no código.

Resultados que dependem de escalonamento de threads (E07) variam de uma execução para outra; os
critérios desses cenários comparam grandezas relativas, não valores exatos.
