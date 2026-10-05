# Fundamentos

## Modelo de interação

O modelo de interação descreve o que se supõe sobre três grandezas: tempo de processamento,
atraso de mensagens e deriva de relógio.

| | Síncrono | Assíncrono |
| --- | --- | --- |
| Tempo de processamento | limite conhecido | sem limite útil |
| Atraso de mensagem | limite conhecido | sem limite útil |
| Deriva de relógio | limite conhecido | sem limite útil |
| Consequência | timeout detecta falha com certeza | timeout só gera suspeita |

O cliente deste laboratório **age como se** o sistema fosse síncrono: ele fixa um timeout de
500 ms e trata a ausência de resposta nesse prazo como falha. O cenário E01 mostra por que isso
é razoável na maior parte do tempo — o p95 normal fica perto de 30 ms, bem abaixo do limite. Os
demais cenários mostram quando a suposição quebra: pausa, lentidão, perda e queda fazem o atraso
real exceder o limite assumido. Sistemas reais vivem nessa região intermediária.

## Por que timeout não prova falha

Quando o timeout dispara, o cliente sabe uma única coisa: **não recebeu resposta no prazo**. As
causas possíveis incluem:

| Causa | O servidor executou? | Experimento |
| --- | --- | --- |
| requisição perdida no canal | não | E05 |
| servidor lento | sim, depois do prazo | E02, E05 |
| rede lenta na volta | sim, dentro do prazo | E05 |
| resposta perdida no canal | sim | E05 |
| processo morto no meio | talvez | E04 |

Por isso o timeout é um **detector de falhas imperfeito**: ele produz suspeita, não prova. É
completo (um servidor realmente caído acaba sendo suspeito), mas não é exato (servidores vivos
e lentos também são). Diminuir o timeout aumenta os falsos positivos; aumentá-lo retém recursos
do chamador por mais tempo.

## Classificação de falhas

| Classe | Descrição | Onde aparece no laboratório |
| --- | --- | --- |
| Crash / fail-stop | o processo para; em fail-stop, a parada é detectável com certeza | E04, E08, E09 (servidor encerrado ou morto) |
| Omissão de envio | a mensagem que deveria sair não sai | E05 (a resposta é produzida, mas o proxy nunca a entrega ao cliente) |
| Omissão de recepção | a mensagem chega ao host mas não é processada | E05 (o proxy aceita a conexão e os bytes da requisição, mas nunca os processa) |
| Temporização | resposta fora do intervalo assumido | E02, E05 (servidor ou rede lentos) |
| Resposta | valor ou transição de estado incorretos | E06 (empréstimo duplicado pelo retry) |
| Bizantina | comportamento arbitrário ou malicioso | fora do escopo; E10 trata o atacante na fronteira, não um nó bizantino |

Uma observação importante do E04: o crash do processo **parece** fail-stop no laboratório porque
o sistema operacional do host continua vivo e recusa a conexão. Se a máquina inteira caísse, não
haveria recusa — só silêncio, e a mesma falha apareceria como timeout.

## Retry, backoff e jitter

Retry aumenta a disponibilidade diante de falhas **transitórias** (E03, E04). Ele tem três
riscos, todos medidos:

1. **Falha persistente:** repetir não muda o resultado e multiplica o trabalho do servidor (E02).
2. **Operação não idempotente:** cada repetição aplica o efeito de novo (E06).
3. **Sincronização entre clientes:** milhares de clientes repetindo ao mesmo tempo amplificam a
   queda que causou o erro (E07).

A política implementada em [`cliente/resiliencia.py`](../cliente/resiliencia.py) segue o
`retry.py` do enunciado:

```text
espera(n) = min(teto, 0,2 × 2ⁿ) + uniforme(0; 0,1)      n = 0, 1, 2, ...
```

- **limite de tentativas:** padrão 4;
- **backoff exponencial:** cada espera dobra, até o teto de 5 s;
- **jitter:** a parcela aleatória desalinha clientes que falharam juntos;
- **o que é repetido:** timeout, falha de conexão e os status 502, 503 e 504. Erros 4xx nunca são
  repetidos, porque são determinísticos.

## Circuit breaker

Depois de `limite_de_falhas` falhas seguidas, o disjuntor **abre** e passa a recusar chamadas
localmente, sem tocar a rede. Passado `tempo_aberto`, ele fica **meio-aberto** e deixa passar
uma chamada de teste: se ela tiver sucesso, **fecha**; se falhar, reabre. O E08 mostra o ciclo
completo e o ganho: de 12 para 3 tentativas na rede contra uma dependência caída.

## Padrões combinados e seus riscos

| Padrão | Problema que resolve | Risco de uso incorreto | Onde |
| --- | --- | --- | --- |
| Timeout | espera indefinida | curto demais: falso fracasso; longo demais: recursos presos | todos |
| Retry | falha transitória | duplicação e tempestade de tráfego | E03, E06, E07 |
| Backoff + jitter | retries simultâneos | recuperação mais lenta se exagerado | E03, E07 |
| Circuit breaker | pressão sobre dependência caída | bloquear a recuperação se a política for ruim | E08 |
| Failover | réplica indisponível | esconder a causa da falha | E09 |
| Idempotency key | repetição de comando não idempotente | retenção curta demais ou gravação fora da transação | E06 |

## Chave de idempotência

O cliente gera uma chave única por **intenção de negócio** e a envia em `Idempotency-Key`. O
servidor grava a chave, a impressão do pedido (hash de livro e leitor) e o id do empréstimo **na
mesma transação** do empréstimo. Numa repetição:

- mesma chave e mesmo pedido: devolve o empréstimo já criado, com `Idempotent-Replayed: true`;
- mesma chave e pedido diferente: 422, porque reutilizar a chave é erro do cliente;
- falha no efeito (por exemplo, 409 por falta de exemplar): nada é gravado, e a chave continua
  livre para uma nova tentativa.

Se duas requisições com a mesma chave correm ao mesmo tempo, a chave primária da tabela garante
que só uma grava; a outra cai no `IntegrityError`, a transação inteira é desfeita e o servidor
devolve o resultado da vencedora.

## Segurança: objetivos e canal

| Objetivo | Pergunta | Tratado aqui? |
| --- | --- | --- |
| Confidencialidade | quem pode ler? | não — o E10 mostra o token em texto claro sem TLS |
| Integridade | quem pode alterar? | sim — escritas exigem papel autorizado |
| Autenticidade | quem é você? | sim — token Bearer |
| Autorização | o que você pode fazer? | sim — papéis bibliotecario, atendente e consulta |
| Disponibilidade | o serviço resiste a abuso? | parcial — limites na rota de laboratório e na validação |
| Não repúdio / auditoria | dá para provar quem fez? | parcial — log com correlação, sem identidade |

TLS protegeria confidencialidade e integridade **do canal** e autenticaria o servidor; mesmo com
ele, a autorização continuaria sendo responsabilidade da aplicação. Um cliente autenticado pode
continuar sem permissão — o 403 do E10 é exatamente esse caso.
