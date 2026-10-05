# Glossário

| Termo | Significado neste trabalho |
| --- | --- |
| **Backoff exponencial** | Espera entre tentativas que dobra a cada falha: 0,2 s, 0,4 s, 0,8 s... até um teto. |
| **Bulkhead** | Isolar recursos por fluxo para que a falha de um não esgote os outros. Citado, não implementado. |
| **Chamada lógica** | Uma intenção do cliente, que pode gerar várias tentativas. Identificada pela correlação. |
| **Circuit breaker (disjuntor)** | Componente do chamador que, após falhas seguidas, recusa chamadas localmente por um tempo e depois testa a dependência com uma única chamada. |
| **Classificação** | Enquadramento de uma falha observada no modelo fundamental: crash, omissão, temporização, resposta ou bizantina. É inferência, não observação. |
| **Conexão interrompida** | A conexão existia e foi fechada sem resposta, por exemplo porque o processo do servidor morreu. |
| **Conexão recusada** | O host respondeu, mas nada escuta na porta (RST, `WinError 10061`). No Windows leva ~2 s para ser reportada em localhost. |
| **Correlação** | Identificador enviado em `X-Request-ID` e repetido em todas as tentativas da mesma chamada; liga o registro do cliente ao log do servidor. |
| **Crash** | O processo para de executar. **Fail-stop** é o caso em que a parada é detectável com certeza. |
| **Detector de falhas imperfeito** | Mecanismo que produz suspeita de falha, não prova. O timeout é o exemplo canônico. |
| **Erro de aplicação** | Resposta HTTP 5xx: o servidor está vivo e declara que não executou o serviço. |
| **Erro do cliente** | Resposta HTTP 4xx: o pedido está errado ou não é permitido. Repetir não adianta. |
| **Failover** | Tentar outra réplica quando a atual falha. |
| **Falha de modo comum** | Uma única causa que derruba vários componentes redundantes ao mesmo tempo, como o banco compartilhado pelas réplicas do E09. |
| **Falha transitória** | Falha que pode não se repetir na próxima tentativa: 503, timeout, conexão recusada durante uma reinicialização. |
| **Idempotência** | Repetir a operação deixa o sistema no mesmo estado que executá-la uma vez. |
| **Idempotency-Key** | Chave enviada pelo cliente por intenção de negócio; o servidor a grava com o resultado e devolve o mesmo resultado nas repetições. |
| **Idempotent-Replayed** | Cabeçalho da resposta que indica que o resultado veio de uma execução anterior. |
| **Impressão do pedido** | Hash dos dados do pedido guardado junto com a chave, para recusar a mesma chave com outro conteúdo. |
| **Jitter** | Parcela aleatória somada à espera para desalinhar clientes que falharam juntos. |
| **Meio-aberto** | Estado do disjuntor em que uma única chamada de teste é permitida. |
| **Modelo assíncrono** | Sem limite conhecido útil para processamento, atraso de mensagem e deriva de relógio. |
| **Modelo síncrono** | Com limites conhecidos para essas três grandezas. |
| **Omissão de envio** | Uma mensagem que deveria ser enviada não é. |
| **Omissão de recepção** | Uma mensagem chega ao host, mas não é processada. |
| **Papel** | Conjunto de permissões associado a um token: bibliotecario, atendente ou consulta. |
| **Percentil (p50, p95, p99)** | Valor abaixo do qual estão 50%, 95% ou 99% das medições de latência. |
| **Proxy de falhas** | Intermediário TCP de [`experimentos/proxy.py`](../experimentos/proxy.py) que perde, atrasa ou observa mensagens. |
| **Rota de laboratório** | `/experimento/instavel`: injeta atraso e falha; só existe com `BIBLIOTECA_LABORATORIO=1`. |
| **Tempestade de retries** | Rajada de tráfego causada por muitos clientes repetindo ao mesmo tempo. |
| **Temporização (falha de)** | Resposta fora do intervalo assumido. |
| **Tentativa** | Uma requisição HTTP efetivamente enviada; uma chamada lógica pode ter várias. |
| **Timeout de conexão** | O prazo acabou antes de a conexão TCP ser estabelecida. |
| **Timeout de leitura** | A conexão foi estabelecida e a requisição enviada, mas a resposta não chegou no prazo. |
| **TLS / mTLS** | Canal com confidencialidade e integridade; no mTLS, os dois lados se autenticam por certificado. |
| **401 / 403** | Sem identidade válida / identidade válida sem permissão. |
