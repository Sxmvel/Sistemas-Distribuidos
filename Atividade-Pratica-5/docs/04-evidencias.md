# Evidências dos experimentos

> Documento gerado automaticamente por `experimentos/executar_todos.py`.
> Não edite à mão: a próxima execução sobrescreve o arquivo.

Execução: 2026-10-05T20:26:54-03:00  
Duração total: 70.0 s  
Python 3.14.3 · FastAPI 0.142.2 · requests 2.34.2 · Windows 11  
Verificações: 69 — falhas: 0 · Tentativas medidas: 261

---

## Tabela de classificação

A coluna **Observação** traz apenas o que foi medido nesta execução. **Classificação** e **Conclusão** são inferências feitas a partir dessa observação e do modelo de falhas.

| Cenário | Hipótese | Falha injetada | Observação (medida) | Classificação (inferência) | Conclusão (inferência) |
| --- | --- | --- | --- | --- | --- |
| **E01** Cenário de referência sem falha | Sem falha injetada, todas as chamadas terminam com sucesso, o servidor registra exatamente as requisições que o cliente enviou e a latência fica muito abaixo do timeout de 500 ms. | nenhuma | 40/40 chamadas com 200; p50=15.0 ms, p95=29.8 ms, p99=33.5 ms; servidor registrou 40 requisições, mediana interna de 1.4 ms. | Sem falha. Linha de base que sustenta o modelo síncrono assumido pelo cliente: atraso limitado e conhecido, bem abaixo do timeout. | O timeout de 500 ms está cerca de 17x acima do p95 normal. Por isso, um timeout nos cenários seguintes indica a falha injetada, e não flutuação comum de latência. |
| **E02** Atraso controlado no servidor | Um atraso de 800 ms, maior que o timeout de 500 ms, aparece no cliente como timeout de leitura, embora o servidor conclua a requisição com 200. Como o atraso é persistente, repetir não ajuda: cada retry é mais uma execução completa no servidor. | atraso_ms=300 e atraso_ms=800 na rota /experimento/instavel | 300 ms -> sucesso em 307 ms; 800 ms -> timeout em 537 ms no cliente e 200 no log do servidor; 800 ms com timeout 1,5 s -> sucesso; retry: 4 timeouts no cliente, 4 execuções 200 no servidor, 3.6 s até desistir. | Falha de temporização: o processo está correto, mas responde fora do intervalo que o cliente assumiu. Para o cliente, é indistinguível de omissão. | O timeout mede a paciência do cliente, não o estado do servidor. Contra atraso persistente, o retry piorou o quadro: multiplicou por 4 a carga e adiou a desistência de 0,5 s para 3.6 s. |
| **E03** Erro de aplicação probabilístico, sem e com retry | Com prob_falha=0,5, cerca de metade das chamadas sem retry falha com 503. Com até 4 tentativas e backoff exponencial, a taxa de sucesso sobe para perto de 1 - 0,5^4 = 94%, ao custo de mais requisições no servidor e de latência maior nas chamadas que precisaram repetir. | prob_falha=0.5 com semente fixa no servidor; prob_falha=1.5 para o caso de entrada inválida | sem retry: 45% de sucesso, erros 503; com retry: 95% de sucesso, 38 requisições para 20 chamadas, pior chamada em 1668 ms; 422 com 1 tentativa. | Omissão transitória do serviço, sinalizada explicitamente como erro de aplicação (503). O processo e o canal estão corretos; é o único caso em que o cliente recebe informação positiva sobre o que aconteceu. | Retry melhorou o resultado de 45% para 95% porque a falha é transitória e a leitura é idempotente. O custo apareceu como carga extra no servidor e latência maior nas chamadas azaradas. |
| **E04** Indisponibilidade e crash do servidor | Sem processo escutando na porta, o cliente não recebe status HTTP: a falha é de transporte. Se o servidor volta dentro da janela de retry, o backoff transforma a indisponibilidade em sucesso. Se o processo morre no meio de uma requisição, o cliente vê a conexão interrompida, sem saber se o efeito foi aplicado. | servidor encerrado; servidor religado durante o backoff; processo morto (kill) no meio de uma requisição de 3 s | fora do ar: timeout-de-conexao em 515 ms (timeout 0,5 s) e conexao-recusada em 2044 ms (timeout 3 s); retry durante a reinicialização: sucesso na tentativa 3; kill no meio: conexao-interrompida em 704 ms, sem registro no servidor. | Crash do processo. No laboratório parece fail-stop porque o sistema operacional ainda responde com recusa (RST); se o host inteiro caísse, a mesma falha apareceria como timeout. | Indisponibilidade é distinguível de erro de aplicação (não há status HTTP), mas a forma como aparece depende do timeout. O retry com backoff resolveu porque a queda era temporária; o crash no meio da requisição deixa o efeito em aberto. |
| **E05** Timeout ambíguo: quatro causas, uma observação | Requisição perdida no canal, servidor lento, rede lenta e resposta perdida produzem a mesma observação no cliente: timeout de leitura aos 500 ms. Só o log do servidor separa parte dos casos, e nem ele separa todos. | proxy TCP entre cliente e servidor nos modos perder-requisicao, atraso (1,2 s) e perder-resposta; atraso_ms=1200 no servidor | cliente: timeout-de-leitura nos quatro casos, entre 515 e 539 ms; servidor: requisição perdida sem registro, servidor lento com 200 em 1202 ms, rede lenta e resposta perdida com 200 em menos de 100 ms. | Omissão de recepção (requisição aceita pelo TCP e nunca processada), temporização no processo (servidor lento), temporização no canal (rede lenta) e omissão de envio no caminho de volta (resposta produzida e nunca entregue). Para o cliente, as quatro são ausência de resposta dentro do prazo. | Timeout não permite afirmar que o servidor falhou: em três dos quatro casos ele executou com sucesso. Rede lenta e resposta perdida são indistinguíveis até no log do servidor. Para escritas, só uma chave de idempotência torna o retry seguro sem saber qual caso ocorreu. |
| **E06** Retry em operação não idempotente | Se o servidor grava o empréstimo e demora 800 ms para responder, um cliente com timeout de 500 ms e retry registra um empréstimo novo a cada tentativa, embora veja só falhas. Com Idempotency-Key, as repetições devolvem o resultado da primeira execução e o domínio fica com um único empréstimo. | atraso de 800 ms depois da gravação do empréstimo (BIBLIOTECA_ATRASO_NA_ESCRITA=0.8) | sem chave: 3 timeouts no cliente, 3 empréstimos de Ana gravados, Bruno recebeu 409; com chave: 3 timeouts no cliente, 1 empréstimo gravado, confirmação 201 com o mesmo id; chave em outro pedido: 422. | Falha de temporização percebida pelo cliente que, somada a uma operação não idempotente e a retry cego, vira falha de resposta do sistema: transição de estado incorreta (empréstimo duplicado). | Aqui o retry piorou o resultado: transformou uma falha de temporização em estado errado no domínio, com dano a um terceiro. O retry só é seguro em escrita quando a operação é idempotente por construção, como com a Idempotency-Key gravada na mesma transação do efeito. |
| **E07** Tempestade de retries: imediato contra backoff com jitter | Com 20 clientes começando juntos e 60% de falha, retries imediatos concentram as tentativas em poucos milissegundos. Backoff exponencial com jitter espalha as mesmas tentativas no tempo e reduz o pico de requisições que o servidor recebe. | prob_falha=0.6; 20 clientes disparados ao mesmo tempo; até 4 tentativas por cliente | imediato: 40 requisições em 77 ms, pico de 40 em 100 ms, 19/20 sucessos, pior cliente em 87 ms; backoff: 43 requisições em 1659 ms, pico de 20, 17/20 sucessos, pior cliente em 1674 ms. | Não é falha de um componente: é efeito emergente da política de retry (amplificação de carga). Num servidor no limite, esse pico vira falha de temporização ou omissão para todos os clientes. | Backoff com jitter reduziu o pico de 40 para 20 requisições por 100 ms com sucesso equivalente, ao custo de recuperação mais lenta. Retry imediato em massa é o mecanismo pelo qual uma falha parcial vira sobrecarga. |
| **E08** Circuit breaker diante de dependência fora do ar | Com a dependência fora do ar, sem disjuntor toda chamada paga o timeout na rede. Um disjuntor que abre após 3 falhas seguidas faz as chamadas seguintes falharem na hora, sem tocar a rede, e fecha sozinho quando a chamada de teste (meio-aberto) tem sucesso. | servidor encerrado durante 12 chamadas; religado em seguida | sem disjuntor: 12 tentativas na rede, 6137 ms somados; com disjuntor: 3 na rede, 9 rejeitadas localmente, 1545 ms somados; estados: fechado -> aberto -> meio-aberto -> aberto -> meio-aberto -> fechado. | Crash da dependência, tratado no chamador. O disjuntor não corrige a falha: troca espera na rede por falha local imediata e alivia a dependência enquanto ela se recupera. | O disjuntor reduziu o tempo gasto esperando a dependência de 6137 para 1545 ms e limitou a pressão sobre ela durante a recuperação. O risco é a política: tempo aberto longo demais atrasa a volta; curto demais vira retry disfarçado. |
| **E09** Falha simultânea de dois componentes | Com duas réplicas e failover no cliente, a queda de uma é mascarada: o cliente troca de réplica e só paga latência. Com as duas fora ao mesmo tempo, não há a quem recorrer e o retry só adia o erro. Com uma réplica lenta e a outra caída, o cliente termina com o erro da última tentativa e perde o diagnóstico da primeira. | réplica A encerrada; réplicas A e B encerradas; réplica A lenta (proxy com 1 s) e B encerrada | A e B no ar: A=sucesso; A fora: A=timeout-de-conexao / B=sucesso, empréstimo 201; A e B fora: A=timeout-de-conexao / B=timeout-de-conexao / A=timeout-de-conexao / B=timeout-de-conexao em 2.3 s; A lenta e B fora: A lenta=timeout-de-leitura / B=timeout-de-conexao. | Combinação de falhas independentes: crash + crash e temporização + crash. A redundância tolera um crash; duas falhas simultâneas excedem a hipótese de falhas do projeto. | A redundância mascarou um crash ao custo de latência, mas não duas falhas simultâneas. Com falhas de tipos diferentes, o erro final esconde a primeira causa: o diagnóstico depende do registro por tentativa. As réplicas compartilham o banco, então uma falha nele derrubaria as duas de uma vez (falha de modo comum). |
| **E10** Controle de segurança: token, autorização por papel e validação | Sem o controle, qualquer processo que alcance a porta altera o acervo. Com token Bearer e lista de papéis, escritas sem credencial válida recebem 401 e credenciais sem permissão recebem 403. O controle não protege o token em trânsito: em HTTP puro, quem observa o canal lê o token. | requisições sem credencial, com credencial inválida, com papel insuficiente e com entrada maliciosa; escuta do canal por proxy | sem credencial, credencial inválida, esquema Basic e token padrão -> 401; consulta e atendente no acervo -> 403; bibliotecário -> 201; atendente em empréstimo -> 201; leitura sem token -> 200; entradas maliciosas -> 422; tokens ausentes do log; token capturado em texto claro pelo proxy; rota de laboratório desligada -> 404. | Ameaças de falsificação de identidade e elevação de privilégio, tratadas por autenticação (autenticidade) e autorização por papel. Ameaça residual: escuta do canal (confidencialidade), que exige TLS. | O controle tratou autenticidade (401 para quem não prova identidade) e autorização (403 para quem não tem permissão), preservando a integridade do acervo. Não tratou confidencialidade: em HTTP puro o token é legível por quem observa o canal, então a próxima camada necessária é TLS. |

## Métricas por cenário

| Cenário | Chamadas | Tentativas | Tentativas com sucesso | Tipos de erro | p50 (ms) | p95 (ms) | máx (ms) |
| --- | :-: | :-: | :-: | --- | ---: | ---: | ---: |
| E01 | 40 | 40 | 40 | - | 15.0 | 29.8 | 33.5 |
| E02 | 4 | 7 | 2 | timeout-de-leitura (5) | 534.5 | 824.9 | 824.9 |
| E03 | 41 | 59 | 28 | erro-de-aplicacao (30), erro-do-cliente (1) | 15.6 | 28.0 | 29.0 |
| E04 | 5 | 7 | 2 | timeout-de-conexao (3), conexao-recusada (1), conexao-interrompida (1) | 512.3 | 2044.2 | 2044.2 |
| E05 | 5 | 5 | 1 | timeout-de-leitura (4) | 516.1 | 538.6 | 538.6 |
| E06 | 5 | 9 | 1 | timeout-de-leitura (6), erro-do-cliente (2) | 513.8 | 819.5 | 819.5 |
| E07 | 40 | 83 | 36 | erro-de-aplicacao (47) | 24.7 | 39.7 | 43.3 |
| E08 | 26 | 26 | 1 | timeout-de-conexao (16), circuito-aberto (9) | 503.6 | 515.3 | 516.8 |
| E09 | 5 | 11 | 3 | timeout-de-conexao (7), timeout-de-leitura (1) | 512.4 | 516.4 | 516.4 |
| E10 | 14 | 14 | 3 | erro-do-cliente (11) | 14.4 | 26.7 | 28.9 |

## Tentativas individuais

Duração, resultado e tipo de erro de cada tentativa. Chamadas em lote (E01, parte de E03, E07 e a rodada sem disjuntor do E08) aparecem só nas métricas acima e no arquivo `logs/tentativas.csv`.

| Cenário | Chamada | Correlação | Nº | Duração (ms) | Status | Tipo de erro | Espera seguinte (s) |
| --- | --- | --- | :-: | ---: | :-: | --- | ---: |
| E02 | atraso 300 ms, timeout 0,5 s | `0d609c09c875` | 1 | 307.1 | 200 | - | - |
| E02 | atraso 800 ms, timeout 0,5 s | `e7b9bbfb444d` | 1 | 537.1 | sem resposta | timeout-de-leitura | - |
| E02 | atraso 800 ms, timeout 1,5 s | `3e1863592012` | 1 | 824.9 | 200 | - | - |
| E02 | atraso 800 ms, timeout 0,5 s, 4 tentativas com backoff | `366b1f3e456d` | 1 | 536.0 | sem resposta | timeout-de-leitura | 0.28 |
| E02 | atraso 800 ms, timeout 0,5 s, 4 tentativas com backoff | `366b1f3e456d` | 2 | 515.9 | sem resposta | timeout-de-leitura | 0.43 |
| E02 | atraso 800 ms, timeout 0,5 s, 4 tentativas com backoff | `366b1f3e456d` | 3 | 534.5 | sem resposta | timeout-de-leitura | 0.82 |
| E02 | atraso 800 ms, timeout 0,5 s, 4 tentativas com backoff | `366b1f3e456d` | 4 | 503.2 | sem resposta | timeout-de-leitura | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `60f8cd27dd30` | 1 | 15.7 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `dc6da84d431f` | 1 | 15.1 | 503 | erro-de-aplicacao | 0.21 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `dc6da84d431f` | 2 | 3.6 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `88d3ef2021c9` | 1 | 17.8 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `090d8c9a9a05` | 1 | 15.2 | 503 | erro-de-aplicacao | 0.25 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `090d8c9a9a05` | 2 | 19.9 | 503 | erro-de-aplicacao | 0.46 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `090d8c9a9a05` | 3 | 22.1 | 503 | erro-de-aplicacao | 0.88 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `090d8c9a9a05` | 4 | 22.4 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `b546ed11dd97` | 1 | 3.8 | 503 | erro-de-aplicacao | 0.22 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `b546ed11dd97` | 2 | 5.0 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `a092be2b8e0d` | 1 | 4.4 | 503 | erro-de-aplicacao | 0.23 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `a092be2b8e0d` | 2 | 4.7 | 503 | erro-de-aplicacao | 0.46 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `a092be2b8e0d` | 3 | 4.1 | 503 | erro-de-aplicacao | 0.86 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `a092be2b8e0d` | 4 | 4.6 | 503 | erro-de-aplicacao | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `166667ebd080` | 1 | 4.1 | 503 | erro-de-aplicacao | 0.23 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `166667ebd080` | 2 | 22.3 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `7b8ad2f051f5` | 1 | 3.1 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `caecb4ff4b79` | 1 | 29.0 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `bf850062d7b6` | 1 | 4.0 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `935741b8ca0b` | 1 | 28.3 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `9068987fd340` | 1 | 13.8 | 503 | erro-de-aplicacao | 0.20 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `9068987fd340` | 2 | 27.8 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `d19628fbb137` | 1 | 3.9 | 503 | erro-de-aplicacao | 0.30 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `d19628fbb137` | 2 | 26.3 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `4a9c9e1c679b` | 1 | 15.4 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `68190ef7f899` | 1 | 4.0 | 503 | erro-de-aplicacao | 0.24 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `68190ef7f899` | 2 | 21.1 | 503 | erro-de-aplicacao | 0.46 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `68190ef7f899` | 3 | 4.8 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `38c4a495df88` | 1 | 4.1 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `c963f833c68f` | 1 | 3.6 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `8ee0f3cd92b3` | 1 | 23.3 | 503 | erro-de-aplicacao | 0.23 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `8ee0f3cd92b3` | 2 | 16.3 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `04c1398b3003` | 1 | 15.0 | 503 | erro-de-aplicacao | 0.24 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `04c1398b3003` | 2 | 24.6 | 200 | - | - |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `7444d1e57858` | 1 | 5.1 | 503 | erro-de-aplicacao | 0.27 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `7444d1e57858` | 2 | 24.4 | 503 | erro-de-aplicacao | 0.45 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `7444d1e57858` | 3 | 25.0 | 503 | erro-de-aplicacao | 0.84 |
| E03 | com retry (4 tentativas, backoff 0,2 s x 2^n + jitter 0,1 s) | `7444d1e57858` | 4 | 27.8 | 200 | - | - |
| E03 | prob_falha=1.5 com retry | `c6a597ccf4c7` | 1 | 14.1 | 422 | erro-do-cliente | - |
| E04 | servidor no ar | `d4e2e3a14688` | 1 | 21.7 | 200 | - | - |
| E04 | servidor fora, timeout 0,5 s | `651597bf75bc` | 1 | 514.5 | sem resposta | timeout-de-conexao | - |
| E04 | servidor fora, timeout de conexão 3 s | `e12e0a13cefe` | 1 | 2044.2 | sem resposta | conexao-recusada | - |
| E04 | retry enquanto o servidor é religado | `df82d078174f` | 1 | 512.3 | sem resposta | timeout-de-conexao | 0.26 |
| E04 | retry enquanto o servidor é religado | `df82d078174f` | 2 | 508.8 | sem resposta | timeout-de-conexao | 0.44 |
| E04 | retry enquanto o servidor é religado | `df82d078174f` | 3 | 5.2 | 200 | - | - |
| E04 | kill no meio de uma requisição de 3 s | `19f949ffc7ff` | 1 | 703.9 | sem resposta | conexao-interrompida | - |
| E05 | proxy normal | `3faa943ad444` | 1 | 20.8 | 200 | - | - |
| E05 | requisição perdida no canal | `0b17a8acafc3` | 1 | 538.6 | sem resposta | timeout-de-leitura | - |
| E05 | servidor lento (1,2 s) | `faa73641d80b` | 1 | 530.7 | sem resposta | timeout-de-leitura | - |
| E05 | rede lenta (1,2 s na volta) | `a24296ad48a3` | 1 | 514.6 | sem resposta | timeout-de-leitura | - |
| E05 | resposta perdida no canal | `a4dc0c7071e8` | 1 | 516.1 | sem resposta | timeout-de-leitura | - |
| E06 | POST empréstimo de Ana, sem chave, 3 tentativas | `2d14a0572b79` | 1 | 503.0 | sem resposta | timeout-de-leitura | 0.30 |
| E06 | POST empréstimo de Ana, sem chave, 3 tentativas | `2d14a0572b79` | 2 | 528.8 | sem resposta | timeout-de-leitura | 0.43 |
| E06 | POST empréstimo de Ana, sem chave, 3 tentativas | `2d14a0572b79` | 3 | 522.9 | sem resposta | timeout-de-leitura | - |
| E06 | POST empréstimo de Bruno (leitor legítimo) | `69b2dd9a97af` | 1 | 5.6 | 409 | erro-do-cliente | - |
| E06 | POST empréstimo de Ana, com chave, 3 tentativas | `a1f2a9cd21f8` | 1 | 507.6 | sem resposta | timeout-de-leitura | 0.20 |
| E06 | POST empréstimo de Ana, com chave, 3 tentativas | `a1f2a9cd21f8` | 2 | 513.8 | sem resposta | timeout-de-leitura | 0.46 |
| E06 | POST empréstimo de Ana, com chave, 3 tentativas | `a1f2a9cd21f8` | 3 | 526.7 | sem resposta | timeout-de-leitura | - |
| E06 | POST com a mesma chave e timeout 2 s | `f0d962b03f3a` | 1 | 819.5 | 201 | - | - |
| E06 | mesma chave, outro leitor | `db0f22846877` | 1 | 6.2 | 422 | erro-do-cliente | - |
| E08 | com disjuntor | `503c8a381a5f` | 1 | 515.3 | sem resposta | timeout-de-conexao | - |
| E08 | com disjuntor | `f14e24404ac5` | 1 | 515.2 | sem resposta | timeout-de-conexao | - |
| E08 | com disjuntor | `33dfe3b8b753` | 1 | 514.2 | sem resposta | timeout-de-conexao | - |
| E08 | com disjuntor | `84c4675133b1` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `c1ad57db8fe2` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `cba65e64143f` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `0370904ebcbf` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `00e290bc3db5` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `9a753b923654` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `0bdafb36fb8e` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `0ab239fda579` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | com disjuntor | `bbdcc04615e8` | 1 | 0.0 | sem resposta | circuito-aberto | - |
| E08 | teste meio-aberto, servidor ainda fora | `4356884e5d93` | 1 | 514.7 | sem resposta | timeout-de-conexao | - |
| E08 | teste meio-aberto, servidor de volta | `2fc5b340eda0` | 1 | 15.0 | 200 | - | - |
| E09 | A e B no ar | `db770fa3b21a` | 1 | 4.9 | 200 | - | - |
| E09 | A fora, B no ar | `5ea3c5938b1e` | 1 | 515.0 | sem resposta | timeout-de-conexao | - |
| E09 | A fora, B no ar | `5ea3c5938b1e` | 2 | 52.2 | 200 | - | - |
| E09 | POST empréstimo com A fora | `db32b156407e` | 1 | 512.7 | sem resposta | timeout-de-conexao | - |
| E09 | POST empréstimo com A fora | `db32b156407e` | 2 | 28.6 | 201 | - | - |
| E09 | A e B fora | `cfe822bbaa1e` | 1 | 501.9 | sem resposta | timeout-de-conexao | - |
| E09 | A e B fora | `cfe822bbaa1e` | 2 | 515.7 | sem resposta | timeout-de-conexao | 0.23 |
| E09 | A e B fora | `cfe822bbaa1e` | 3 | 502.9 | sem resposta | timeout-de-conexao | - |
| E09 | A e B fora | `cfe822bbaa1e` | 4 | 516.4 | sem resposta | timeout-de-conexao | - |
| E09 | A lenta (proxy 1 s), B fora | `c00efd93cbd3` | 1 | 514.5 | sem resposta | timeout-de-leitura | - |
| E09 | A lenta (proxy 1 s), B fora | `c00efd93cbd3` | 2 | 512.4 | sem resposta | timeout-de-conexao | - |
| E10 | POST /v1/livros sem Authorization | `27f68af938e2` | 1 | 4.3 | 401 | erro-do-cliente | - |
| E10 | POST /v1/livros com token inexistente | `14bc90eba5d2` | 1 | 26.7 | 401 | erro-do-cliente | - |
| E10 | POST /v1/livros com esquema Basic | `0eafd176b412` | 1 | 14.4 | 401 | erro-do-cliente | - |
| E10 | POST /v1/livros com token padrão de desenvolvimento | `b3680e7e2f10` | 1 | 15.4 | 401 | erro-do-cliente | - |
| E10 | POST /v1/livros com papel consulta | `7b9ed62fd43e` | 1 | 3.5 | 403 | erro-do-cliente | - |
| E10 | POST /v1/livros com papel atendente | `42994d072da0` | 1 | 3.7 | 403 | erro-do-cliente | - |
| E10 | POST /v1/livros com papel bibliotecario | `9d05c7b5efd7` | 1 | 28.9 | 201 | - | - |
| E10 | POST empréstimo com papel atendente | `a7c34c7f94ae` | 1 | 8.5 | 201 | - | - |
| E10 | GET sem token | `f323d45137f7` | 1 | 18.2 | 200 | - | - |
| E10 | campo de controle injetado (versao=99) | `6f4e0ce3f390` | 1 | 15.8 | 422 | erro-do-cliente | - |
| E10 | título com 5000 caracteres | `bb81aa7a3f66` | 1 | 3.2 | 422 | erro-do-cliente | - |
| E10 | ano fora da faixa | `ea7336ca0e74` | 1 | 2.5 | 422 | erro-do-cliente | - |
| E10 | atraso_ms=600000 na rota de laboratório | `6503d3815316` | 1 | 25.8 | 422 | erro-do-cliente | - |
| E10 | rota de laboratório com BIBLIOTECA_LABORATORIO=0 | `e154ba9f09b2` | 1 | 18.6 | 404 | erro-do-cliente | - |

---

## Verificações por cenário

### E01 — Cenário de referência sem falha

**Hipótese:** Sem falha injetada, todas as chamadas terminam com sucesso, o servidor registra exatamente as requisições que o cliente enviou e a latência fica muito abaixo do timeout de 500 ms.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| chamadas concluídas com 200 | `40/40` | `40/40` | ok | Nenhuma falha sem injeção: qualquer erro nos cenários seguintes é atribuível ao que foi injetado. |
| p95 da latência abaixo do timeout | `< 500 ms` | `29.8 ms` | ok | p50=15.0 ms, p95=29.8 ms, p99=33.5 ms. O timeout de 500 ms fica 17x acima do p95: há folga suficiente para não haver falso fracasso. |
| requisições registradas no servidor | `40` | `40` | ok | Cliente e servidor contam o mesmo número de requisições: nenhuma omissão no canal. |
| tempo no servidor menor que o tempo no cliente | `True` | `True` | ok | Mediana no servidor 1.4 ms contra 15.0 ms no cliente. A diferença é conexão TCP, serialização e escalonamento: custo que existe mesmo sem falha. |

### E02 — Atraso controlado no servidor

**Hipótese:** Um atraso de 800 ms, maior que o timeout de 500 ms, aparece no cliente como timeout de leitura, embora o servidor conclua a requisição com 200. Como o atraso é persistente, repetir não ajuda: cada retry é mais uma execução completa no servidor.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| atraso menor que o timeout | `sucesso` | `sucesso` | ok | Resposta em 307 ms: lenta, mas dentro do limite. Lentidão só vira falha quando ultrapassa o que o cliente aceita esperar. |
| atraso maior que o timeout | `timeout-de-leitura` | `timeout-de-leitura` | ok | O cliente desistiu em 537 ms. A conexão foi aceita e a requisição enviada; faltou apenas a resposta dentro do prazo. |
| servidor concluiu a chamada que o cliente deu como perdida | `200` | `200` | ok | O log do servidor mostra status 200 em 801.52 ms para a mesma correlação. O timeout não provou falha: o servidor estava apenas lento. |
| mesmo atraso com timeout maior | `sucesso` | `sucesso` | ok | Mesma condição do servidor, outro resultado: o que mudou foi só a decisão do cliente sobre quanto esperar. |
| retry contra atraso persistente | `falha após 4 tentativas` | `falha após 4 tentativas` | ok | Todas as tentativas estouraram o timeout: o atraso não é transitório, então repetir não muda o resultado. |
| execuções completas no servidor durante o retry | `4` | `4` | ok | O servidor concluiu com 200 as quatro execuções que o cliente contabilizou como falha. O retry quadruplicou o trabalho do servidor sem nenhum ganho para o cliente. |

### E03 — Erro de aplicação probabilístico, sem e com retry

**Hipótese:** Com prob_falha=0,5, cerca de metade das chamadas sem retry falha com 503. Com até 4 tentativas e backoff exponencial, a taxa de sucesso sobe para perto de 1 - 0,5^4 = 94%, ao custo de mais requisições no servidor e de latência maior nas chamadas que precisaram repetir.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| taxa de sucesso sem retry | `entre 20% e 80%` | `45%` | ok | Cada chamada é uma única aposta contra a falha injetada. |
| tipo de erro observado sem retry | `erro-de-aplicacao` | `erro-de-aplicacao` | ok | Existe resposta HTTP 503 com corpo problem+json: o servidor está vivo e declara a falha. Não há ambiguidade sobre o efeito, ao contrário do timeout. |
| taxa de sucesso com retry | `>= 85%` | `95%` | ok | Subiu de 45% para 95%. Retry funciona aqui porque a falha é transitória e independente entre tentativas, e a operação é uma leitura idempotente. |
| tentativas por chamada respeitam o limite | `<= 4` | `4` | ok | O retry é limitado: uma falha persistente não vira laço infinito. |
| esperas seguem backoff exponencial com jitter | `True` | `True` | ok | A n-ésima espera fica em [0,2 x 2^(n-1), 0,2 x 2^(n-1) + 0,1] s, como no retry.py do enunciado. |
| amplificação de carga no servidor | `58 requisições` | `58 requisições` | ok | 20 chamadas lógicas com retry geraram 38 requisições (1.90 por chamada). O preço da disponibilidade é carga extra. |
| erro do cliente não é repetido | `1 tentativa (422)` | `1 tentativa (422)` | ok | 422 é determinístico: repetir a mesma entrada inválida daria o mesmo erro. Só falhas transitórias entram na política de retry. |

### E04 — Indisponibilidade e crash do servidor

**Hipótese:** Sem processo escutando na porta, o cliente não recebe status HTTP: a falha é de transporte. Se o servidor volta dentro da janela de retry, o backoff transforma a indisponibilidade em sucesso. Se o processo morre no meio de uma requisição, o cliente vê a conexão interrompida, sem saber se o efeito foi aplicado.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| linha de base com o servidor no ar | `sucesso` | `sucesso` | ok | Estado inicial. |
| servidor fora com timeout de 0,5 s | `timeout-de-conexao` | `timeout-de-conexao` | ok | Falhou em 515 ms como timeout de conexão. No Windows, a recusa em localhost só é reportada depois de ~2 s de novas tentativas de SYN; com timeout menor que isso, a recusa se disfarça de timeout. |
| servidor fora com timeout de conexão de 3 s | `conexao-recusada` | `conexao-recusada` | ok | Com prazo suficiente, a causa real aparece em 2044 ms: WinError 10061, recusa ativa. A mesma falha recebeu dois nomes diferentes conforme o timeout escolhido. |
| retry com backoff durante a reinicialização | `sucesso após falhas` | `sucesso na tentativa 3` | ok | 2 tentativa(s) sem conexão antes de o servidor voltar e a última com 200, em 1.7 s no total. Aqui o retry melhorou o resultado: a indisponibilidade era temporária. |
| processo morto no meio da requisição | `conexao-interrompida` | `conexao-interrompida` | ok | O cliente percebeu em 704 ms, bem antes do timeout de 5 s, porque o sistema operacional fechou a conexão do processo morto. |
| servidor não registrou a requisição interrompida | `0` | `0` | ok | O log do servidor não tem a linha de conclusão: o processo morreu antes. Numa escrita, o cliente não saberia se o efeito chegou a ser aplicado. |

### E05 — Timeout ambíguo: quatro causas, uma observação

**Hipótese:** Requisição perdida no canal, servidor lento, rede lenta e resposta perdida produzem a mesma observação no cliente: timeout de leitura aos 500 ms. Só o log do servidor separa parte dos casos, e nem ele separa todos.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| referência através do proxy | `sucesso` | `sucesso` | ok | O proxy, sozinho, não introduz falha. |
| observação do cliente nos quatro casos | `timeout-de-leitura` | `timeout-de-leitura` | ok | Mesma categoria e mesma duração (515 a 539 ms). Em todos os casos a conexão TCP foi aceita (pelo proxy), por isso não é timeout de conexão. |
| requisição perdida: registro no servidor | `nenhum` | `nenhum` | ok | O servidor nunca soube da chamada. Para uma escrita, isso significa que o efeito não aconteceu, e repetir é seguro. O cliente, porém, não tem como saber que está neste caso. |
| servidor lento: registro no servidor | `200 com duração >= 1200 ms` | `200 em 1202 ms` | ok | O servidor executou e demorou: a duração interna explica o timeout. |
| rede lenta e resposta perdida: registro no servidor | `200 rápido nos dois` | `200 em 1.3 ms / 200 em 1.6 ms` | ok | Nos dois casos o servidor respondeu em poucos milissegundos e registrou sucesso. Nem o log do servidor distingue a resposta que atrasou da que se perdeu: só quem observa o canal (aqui, o proxy) sabe. |

### E06 — Retry em operação não idempotente

**Hipótese:** Se o servidor grava o empréstimo e demora 800 ms para responder, um cliente com timeout de 500 ms e retry registra um empréstimo novo a cada tentativa, embora veja só falhas. Com Idempotency-Key, as repetições devolvem o resultado da primeira execução e o domínio fica com um único empréstimo.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| o que o cliente viu | `3 timeouts` | `3 timeouts` | ok | Do ponto de vista do cliente, o empréstimo falhou três vezes. |
| o que o servidor fez | `3 x 201` | `3 x 201` | ok | Cada tentativa chegou, gravou e só então atrasou a resposta. O log mostra a mesma correlação com X-Tentativa 1, 2 e 3, todas com 201. |
| empréstimos ativos de Ana | `3` | `3` | ok | Uma intenção de negócio virou três empréstimos. O cliente acha que nada aconteceu; o acervo acha que Ana levou três exemplares do mesmo título. |
| outro leitor tenta emprestar o mesmo livro | `409` | `409` | ok | Efeito colateral visível para terceiros: os exemplares acabaram por causa dos retries. |
| o que o cliente viu com chave | `3 timeouts` | `3 timeouts` | ok | A chave não acelera a resposta: o atraso continua e o cliente continua desistindo. |
| empréstimos ativos de Ana com chave | `1` | `1` | ok | As tentativas 2 e 3 encontraram a chave gravada na mesma transação do empréstimo e devolveram o resultado anterior em vez de repetir o efeito. |
| repetição com prazo suficiente devolve o mesmo empréstimo | `201, mesmo id, Idempotent-Replayed` | `201, mesmo id, Idempotent-Replayed` | ok | O cliente finalmente recebe a resposta da execução que já tinha acontecido, marcada como repetição. |
| chave reutilizada em outro pedido | `422` | `422` | ok | A chave guarda a impressão do pedido. Reaproveitá-la com outro conteúdo é erro do cliente e é recusado. |

### E07 — Tempestade de retries: imediato contra backoff com jitter

**Hipótese:** Com 20 clientes começando juntos e 60% de falha, retries imediatos concentram as tentativas em poucos milissegundos. Backoff exponencial com jitter espalha as mesmas tentativas no tempo e reduz o pico de requisições que o servidor recebe.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| requisições no servidor por chamada lógica (imediato) | `> 1` | `2.00` | ok | 20 chamadas viraram 40 requisições. Toda política de retry amplifica carga durante a falha. |
| pico de requisições em 100 ms (imediato) | `> 20` | `40 de 40` | ok | O pico passou do número de clientes: as repetições caíram na mesma janela de 100 ms do primeiro disparo, somando-se a ele em vez de esperar o servidor se recuperar. |
| pico de requisições em 100 ms (backoff + jitter) | `<= 20 e < 40` | `20 de 43` | ok | O primeiro disparo continua simultâneo, mas nenhuma repetição se soma a ele: as ondas seguintes chegam cada vez mais tarde e desalinhadas pelo jitter. |
| duração da rajada (primeira à última requisição) | `imediato < backoff` | `77 ms imediato, 1659 ms backoff` | ok | A mesma quantidade de trabalho foi comprimida em poucas centenas de milissegundos no retry imediato e espalhada por mais de um segundo com backoff. |
| taxa de sucesso nas duas políticas | `semelhante` | `19/20 imediato, 17/20 backoff` | ok | Com falha aleatória independente, o número de tentativas decide o sucesso, não o intervalo. O backoff não piora o resultado: só muda quando a carga chega. |

### E08 — Circuit breaker diante de dependência fora do ar

**Hipótese:** Com a dependência fora do ar, sem disjuntor toda chamada paga o timeout na rede. Um disjuntor que abre após 3 falhas seguidas faz as chamadas seguintes falharem na hora, sem tocar a rede, e fecha sozinho quando a chamada de teste (meio-aberto) tem sucesso.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| tentativas que chegaram à rede sem disjuntor | `12` | `12` | ok | Cada chamada esperou o timeout de conexão: 6137 ms somados. |
| tentativas que chegaram à rede com disjuntor | `3` | `3` | ok | Depois de 3 falhas seguidas o circuito abriu e as outras 9 chamadas falharam localmente. Custo total: 1545 ms. |
| latência de uma chamada rejeitada pelo circuito aberto | `< 1 ms` | `0.0 ms` | ok | Falha rápida: o chamador libera a thread na hora em vez de segurá-la por 500 ms. |
| teste no meio-aberto com a dependência ainda fora | `aberto` | `aberto` | ok | Uma única chamada de teste (timeout-de-conexao) e o circuito reabre: não houve rajada de tentativas contra a dependência ainda caída. |
| teste no meio-aberto com a dependência de volta | `sucesso / fechado` | `sucesso / fechado` | ok | A chamada de teste passou e o circuito voltou ao normal sem intervenção manual. |
| sequência de estados do disjuntor | `fechado -> aberto -> meio-aberto -> aberto -> meio-aberto -> fechado` | `fechado -> aberto -> meio-aberto -> aberto -> meio-aberto -> fechado` | ok | O ciclo completo de estados do padrão, registrado pelo próprio disjuntor. |

### E09 — Falha simultânea de dois componentes

**Hipótese:** Com duas réplicas e failover no cliente, a queda de uma é mascarada: o cliente troca de réplica e só paga latência. Com as duas fora ao mesmo tempo, não há a quem recorrer e o retry só adia o erro. Com uma réplica lenta e a outra caída, o cliente termina com o erro da última tentativa e perde o diagnóstico da primeira.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| as duas réplicas no ar | `sucesso na 1a tentativa` | `sucesso na 1a tentativa` | ok | Linha de base: a réplica A atende sozinha. |
| uma réplica fora | `sucesso na 2a tentativa` | `sucesso na 2a tentativa` | ok | O cliente pagou 515 ms na réplica caída e foi atendido pela B. A falha foi mascarada; só a latência denuncia que algo aconteceu. |
| escrita durante a falha de uma réplica | `201` | `201` | ok | A escrita feita pela B vai para o mesmo banco que a A usava. O estado sobreviveu à queda porque não morava no processo, e é justamente por isso que o banco compartilhado é um ponto único de falha. |
| duas réplicas fora ao mesmo tempo | `falha após 4 tentativas` | `falha após 4 tentativas` | ok | Duas rodadas de failover com backoff: A=timeout-de-conexao / B=timeout-de-conexao / A=timeout-de-conexao / B=timeout-de-conexao. O retry gastou 2.3 s para chegar ao mesmo erro. |
| réplica lenta e réplica caída | `timeout-de-leitura, depois timeout-de-conexao` | `timeout-de-leitura, timeout-de-conexao` | ok | O erro final entregue ao chamador é 'timeout-de-conexao', da réplica B. A informação de que a A estava viva, mas lenta, só existe no registro por tentativa. |

### E10 — Controle de segurança: token, autorização por papel e validação

**Hipótese:** Sem o controle, qualquer processo que alcance a porta altera o acervo. Com token Bearer e lista de papéis, escritas sem credencial válida recebem 401 e credenciais sem permissão recebem 403. O controle não protege o token em trânsito: em HTTP puro, quem observa o canal lê o token.

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| POST /v1/livros sem Authorization | `401` | `401` | ok | Sem credencial não há identidade: a escrita é recusada antes de tocar o domínio. |
| 401 traz o desafio WWW-Authenticate | `Bearer realm="biblioteca"` | `Bearer realm="biblioteca"` | ok | O servidor diz ao cliente qual esquema de autenticação espera, como manda a semântica do 401. |
| POST /v1/livros com token inexistente | `401` | `401` | ok | Token desconhecido é tratado como ausência de identidade. |
| POST /v1/livros com esquema Basic | `401` | `401` | ok | Só o esquema Bearer é aceito; outra forma de credencial não abre exceção. |
| POST /v1/livros com token padrão de desenvolvimento | `401` | `401` | ok | O laboratório injeta tokens gerados a cada execução, então o valor padrão do código não vale aqui. |
| POST /v1/livros com papel consulta | `403` | `403` | ok | Identidade válida, permissão insuficiente: 403, não 401. Autenticar não é autorizar. |
| POST /v1/livros com papel atendente | `403` | `403` | ok | O atendente registra empréstimos, mas não altera o acervo. |
| POST /v1/livros com papel bibliotecario | `201` | `201` | ok | O único papel com permissão sobre o acervo. |
| atendente registra empréstimo | `201` | `201` | ok | A lista de papéis concede ao atendente exatamente o que a função dele exige. |
| leitura pública sem token | `200` | `200` | ok | Decisão de projeto: o catálogo é público. O controle protege integridade (quem altera), não a confidencialidade do acervo. |
| validação robusta: campo de controle injetado (versao=99) | `422` | `422` | ok | O esquema recusa campos desconhecidos e limites violados mesmo para quem tem permissão: autorização não dispensa validação. |
| validação robusta: título com 5000 caracteres | `422` | `422` | ok | O esquema recusa campos desconhecidos e limites violados mesmo para quem tem permissão: autorização não dispensa validação. |
| validação robusta: ano fora da faixa | `422` | `422` | ok | O esquema recusa campos desconhecidos e limites violados mesmo para quem tem permissão: autorização não dispensa validação. |
| rota de laboratório limita o atraso pedido | `422` | `422` | ok | Sem o limite de 10 s, poucas requisições prenderiam todas as threads do servidor por 10 minutos: negação de serviço pela própria ferramenta de teste. |
| tokens ausentes dos logs do servidor | `nenhum` | `nenhum` | ok | O middleware registra método, caminho, status e correlação, nunca cabeçalhos. Log é um destino comum de vazamento de credencial. |
| token legível por quem observa o canal HTTP | `True` | `True` | ok | O proxy, no papel de intermediário na rede, leu o token do bibliotecário em texto claro. O controle por token depende de confidencialidade do canal: em uso real, TLS é pré-requisito, não opcional. |
| rota de injeção de falha desligada por padrão | `404` | `404` | ok | Fora do laboratório a rota não existe para o cliente. Endpoint de injeção de falha esquecido em produção é superfície de ataque. |

---

## Logs brutos

Cada servidor grava uma linha JSON por requisição em `logs/<cenario>-<servidor>.jsonl`, com instante, correlação (`X-Request-ID`), número da tentativa (`X-Tentativa`), método, caminho, status e duração interna. O cliente envia a mesma correlação em todas as tentativas de uma chamada, então o log do servidor mostra quais tentativas chegaram e como terminaram. As tentativas medidas no cliente ficam em `logs/tentativas.csv`.
