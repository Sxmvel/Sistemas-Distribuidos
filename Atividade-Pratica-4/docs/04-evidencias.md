# Evidências dos experimentos

> Documento gerado automaticamente por `experimentos/executar_todos.py`.
> Não edite à mão: a próxima execução sobrescreve o arquivo.

Execução: 2026-09-16T23:48:03-03:00  
Duração total: 26.9 s  
Python 3.14.3 · grpcio 1.84.0 · Windows  
Verificações: 90 — falhas: 0

## Resumo por cenário

| Cenário | Título | Verificações | Falhas |
| --- | --- | :-: | :-: |
| E01 | Contrato, geracao reproduzivel de stubs e fluxo unario/streaming | 13 | 0 |
| E02 | Erros de dominio traduzidos para status gRPC | 26 | 0 |
| E03 | Deadlines de 100 ms, 1 s e 3 s no mesmo metodo | 10 | 0 |
| E04 | Indisponibilidade do servidor durante o uso do cliente | 9 | 0 |
| E05 | Concorrencia: max_workers do servidor contra clientes simultaneos | 8 | 0 |
| E06 | Retry apos deadline ambiguo, com e sem chave de idempotencia | 10 | 0 |
| E07 | Evolucao do contrato: cliente antigo contra servidor novo | 14 | 0 |

## Latência e status por chamada

| Cenário | Chamada | Deadline | Status | Latência (ms) | Observação |
| --- | --- | --- | --- | ---: | --- |
| E01 | RegistrarEmprestimo | 3 s | `OK` | 5.1 | chamada unaria de escrita |
| E01 | ConsultarEmprestimo | 3 s | `OK` | 1.2 | leitura do recurso recem-criado |
| E01 | ListarEmprestimos | 3 s | `OK` | 1.2 | server streaming com 4 itens |
| E01 | RegistrarDevolucao | 3 s | `OK` | 0.6 | devolucao com 4 dias de atraso |
| E02 | RegistrarEmprestimo — isbn vazio | 2 s | `INVALID_ARGUMENT` | 5.0 | Validacao explicita antes de qualquer efeito: o pedido nem chega ao repositorio |
| E02 | RegistrarEmprestimo — isbn com 3 digitos | 2 s | `INVALID_ARGUMENT` | 1.3 | Formato errado independe do estado do sistema, entao e erro do chamador |
| E02 | RegistrarEmprestimo — leitor fora do formato nome.sobrenome | 2 s | `INVALID_ARGUMENT` | 1.1 | O contrato aceita string, mas a regra de formato e do servico, nao do  |
| E02 | RegistrarEmprestimo — dias acima do prazo maximo | 2 s | `INVALID_ARGUMENT` | 0.7 | int32 no contrato nao restringe faixa; a faixa e validada no servidor |
| E02 | RegistrarEmprestimo — unidade desconhecida | 2 s | `INVALID_ARGUMENT` | 0.7 | Campo novo da v2 tambem e validado, senao a evolucao abriria um buraco |
| E02 | RegistrarEmprestimo — isbn bem formado mas fora do acervo | 2 s | `NOT_FOUND` | 0.7 | Entrada valida e entidade ausente: NOT_FOUND, nao INVALID_ARGUMENT |
| E02 | ConsultarEmprestimo — consulta de codigo inexistente | 2 s | `NOT_FOUND` | 0.8 | Mesma distincao na leitura: o formato esta certo, o recurso e que nao existe |
| E02 | CalcularMultas — calculo de multa sem codigos | 2 s | `INVALID_ARGUMENT` | 0.6 | repeated vazio e indistinguivel de campo ausente em proto3; a obrigatoriedade vira regra de servico |
| E02 | RegistrarEmprestimo — sem exemplar disponivel | 2 s | `FAILED_PRECONDITION` | 0.6 | conflito de estado |
| E02 | RegistrarDevolucao — emprestimo ja devolvido | 2 s | `FAILED_PRECONDITION` | 0.6 | operacao nao idempotente por natureza |
| E02 | RegistrarEmprestimo — chave reusada com outro pedido | 2 s | `ALREADY_EXISTS` | 0.5 | chave de idempotencia divergente |
| E02 | RegistrarEmprestimo — servidor desligado, deadline curto | 1.5 s | `DEADLINE_EXCEEDED` | 1511.9 | nenhum processo escutando na porta |
| E02 | RegistrarEmprestimo — servidor desligado, deadline folgado | 5 s | `UNAVAILABLE` | 546.4 | mesma porta vazia, deadline maior que o backoff de conexao |
| E03 | CalcularMultas (40 codigos) | 0.1 s | `DEADLINE_EXCEEDED` | 109.8 | custo no servidor ~1.20 s |
| E03 | CalcularMultas (40 codigos) | 1 s | `DEADLINE_EXCEEDED` | 1016.3 | custo no servidor ~1.20 s |
| E03 | CalcularMultas (40 codigos) | 3 s | `OK` | 1218.2 | custo no servidor ~1.20 s |
| E03 | CalcularMultas (40 codigos) | sem deadline | `OK` | 1218.2 | chamada sem deadline, para contraste |
| E04 | RegistrarEmprestimo — pedido valido, servidor no ar | 2 s | `OK` | 4.4 | linha de base |
| E04 | RegistrarEmprestimo — pedido invalido, servidor no ar | 2 s | `INVALID_ARGUMENT` | 1.1 | validacao executada pelo servico |
| E04 | RegistrarEmprestimo — pedido valido, servidor fora | 5 s | `UNAVAILABLE` | 2041.8 | sem processo escutando |
| E04 | RegistrarEmprestimo — pedido invalido, servidor fora | 5 s | `UNAVAILABLE` | 0.3 | mesmo pedido invalido de antes |
| E04 | RegistrarEmprestimo — wait_for_ready durante a queda | 20 s | `OK` | 1522.3 | servidor voltou ~1 s depois |
| E04 | CalcularMultas — servidor morto no meio | 10 s | `UNAVAILABLE` | 618.0 | processo encerrado com kill apos ~0,6 s |
| E05 | CalcularMultas x24 com max_workers=2 (p50) | 30 s | `OK` | 1220.6 | 8 clientes simultaneos em um unico canal |
| E05 | CalcularMultas x24 com max_workers=2 (p95) | 30 s | `OK` | 1223.7 | duracao total da rodada: 3.67 s |
| E05 | CalcularMultas x24 com max_workers=16 (p50) | 30 s | `OK` | 308.4 | 8 clientes simultaneos em um unico canal |
| E05 | CalcularMultas x24 com max_workers=16 (p95) | 30 s | `OK` | 310.6 | duracao total da rodada: 0.93 s |
| E06 | RegistrarEmprestimo — 1a tentativa sem chave | 0.15 s | `DEADLINE_EXCEEDED` | 153.0 | servidor leva 0.5 s para responder a escrita |
| E06 | RegistrarEmprestimo — retry cego sem chave | 5 s | `OK` | 503.6 | retry ingenuo do mesmo pedido |
| E06 | RegistrarEmprestimo — 1a tentativa com chave | 0.15 s | `DEADLINE_EXCEEDED` | 166.6 | mesma janela de ambiguidade |
| E06 | RegistrarEmprestimo — retry com a mesma chave | 5 s | `OK` | 502.8 | retry protegido por chave de idempotencia |
| E06 | RegistrarEmprestimo — mesma chave, outro pedido | 5 s | `ALREADY_EXISTS` | 1.0 | chave reaproveitada indevidamente |
| E07 | RegistrarEmprestimo — cliente novo usa o campo unidade | 5 s | `OK` | 5.6 | contrato v2 dos dois lados |

---

## E01 — Contrato, geracao reproduzivel de stubs e fluxo unario/streaming

**Pergunta que o cenário responde:** O contrato .proto descreve o servico e pode ser regenerado do zero?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| gerar_stubs.py conclui sem erro | `0` | `0` | ok | O comando apaga os arquivos gerados e chama grpc_tools.protoc de novo, entao o contrato e regeneravel do zero. |
| stubs regenerados sao byte a byte iguais | `True` | `True` | ok | 5 arquivos gerados a partir dos .proto; mesmos hashes SHA-256 antes e depois, logo nao ha edicao manual no codigo gerado. |
| metodos RPC publicados pelo contrato | `5` | `5` | ok | O servico expoe RegistrarEmprestimo, ConsultarEmprestimo, RegistrarDevolucao, CalcularMultas, ListarEmprestimos — acima do minimo de tres pedido na AP4. |
| mensagens proprias declaradas no .proto | `>= 3` | `11` | ok | Tipos: CalcularMultasRequest, CalcularMultasResponse, ConsultarEmprestimoRequest, ConsultarEmprestimoResponse, Emprestimo, ListarEmprestimosRequest, MultaDoEmprestimo, RegistrarDevolucaoRequest, RegistrarDevolucaoResponse, RegistrarEmprestimoRequest, RegistrarEmprestimoResponse. |
| ListarEmprestimos declarado como server streaming | `True` | `True` | ok | Uma requisicao produz um fluxo de respostas na mesma RPC, sem abrir uma chamada por item. |
| RegistrarEmprestimo devolve OK | `OK` | `OK` | ok | Chamada unaria: uma requisicao, uma resposta. |
| prazo calculado no servidor volta no campo previsto_para | `2026-09-23` | `2026-09-23` | ok | O servidor e dono da regra de prazo; o cliente recebe o resultado ja serializado em Protocol Buffers. |
| enum Situacao chega tipado no cliente | `SITUACAO_ATIVO` | `SITUACAO_ATIVO` | ok | O enum viaja como inteiro no fio e volta a ser simbolo no stub gerado. |
| campo unidade (adicionado na v2) volta preenchido | `anexo` | `anexo` | ok | Campo 9 de Emprestimo, ausente no contrato legado, e usado pelo cliente novo. |
| round-trip preserva os campos do emprestimo | `True` | `True` | ok | Serializacao e desserializacao nao perdem nem alteram campos. |
| server streaming entrega todos os ativos em uma RPC | `4` | `4` | ok | Quatro mensagens Emprestimo chegaram no mesmo fluxo logico, sem uma RPC por item. |
| atraso calculado na devolucao | `4` | `4` | ok | Prazo de 7 dias, devolucao no 11o dia: 4 dias de atraso. |
| multa em double respeita o valor por dia | `2.0` | `2.0` | ok | 4 dias x R$ 0.50 chega ao cliente como double. |

## E02 — Erros de dominio traduzidos para status gRPC

**Pergunta que o cenário responde:** O cliente consegue separar erro de aplicacao de indisponibilidade do servico?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| status de: isbn vazio | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | Validacao explicita antes de qualquer efeito: o pedido nem chega ao repositorio. |
| campo sinalizado em: isbn vazio | `isbn` | `isbn` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: isbn com 3 digitos | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | Formato errado independe do estado do sistema, entao e erro do chamador. |
| campo sinalizado em: isbn com 3 digitos | `isbn` | `isbn` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: leitor fora do formato nome.sobrenome | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | O contrato aceita string, mas a regra de formato e do servico, nao do .proto. |
| campo sinalizado em: leitor fora do formato nome.sobrenome | `leitor` | `leitor` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: dias acima do prazo maximo | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | int32 no contrato nao restringe faixa; a faixa e validada no servidor. |
| campo sinalizado em: dias acima do prazo maximo | `dias` | `dias` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: unidade desconhecida | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | Campo novo da v2 tambem e validado, senao a evolucao abriria um buraco. |
| campo sinalizado em: unidade desconhecida | `unidade` | `unidade` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: isbn bem formado mas fora do acervo | `NOT_FOUND` | `NOT_FOUND` | ok | Entrada valida e entidade ausente: NOT_FOUND, nao INVALID_ARGUMENT. |
| campo sinalizado em: isbn bem formado mas fora do acervo | `isbn` | `isbn` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: consulta de codigo inexistente | `NOT_FOUND` | `NOT_FOUND` | ok | Mesma distincao na leitura: o formato esta certo, o recurso e que nao existe. |
| campo sinalizado em: consulta de codigo inexistente | `codigo` | `codigo` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| status de: calculo de multa sem codigos | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | repeated vazio e indistinguivel de campo ausente em proto3; a obrigatoriedade vira regra de servico. |
| campo sinalizado em: calculo de multa sem codigos | `codigos` | `codigos` | ok | O interceptador devolve x-campo no trailing metadata, entao o cliente sabe o que corrigir sem fazer parsing da mensagem de erro. |
| primeiro emprestimo do unico exemplar e aceito | `OK` | `OK` | ok | Macunaima tem 1 exemplar no acervo. |
| status quando o estado impede a operacao | `FAILED_PRECONDITION` | `FAILED_PRECONDITION` | ok | O pedido esta correto e o livro existe; o que falha e a precondicao de estado. Repetir sem mudar o estado nao adianta. |
| politica de retry sugerida para FAILED_PRECONDITION | `corrigir a chamada, nunca repetir` | `corrigir a chamada, nunca repetir` | ok | Status coerente permite que o cliente decida sozinho entre corrigir, desistir ou repetir. |
| segunda devolucao do mesmo emprestimo | `FAILED_PRECONDITION` | `FAILED_PRECONDITION` | ok | Devolver duas vezes nao e o mesmo que devolver uma vez: o servico recusa em vez de sobrescrever a data. |
| chave de idempotencia reusada com payload diferente | `ALREADY_EXISTS` | `ALREADY_EXISTS` | ok | Reaproveitar a chave com outro conteudo e erro do chamador: o servico recusa em vez de devolver silenciosamente o emprestimo antigo. |
| deadline curto mascara a indisponibilidade | `DEADLINE_EXCEEDED` | `DEADLINE_EXCEEDED` | ok | Em um canal recem-aberto o gRPC leva cerca de 2 s tentando conectar antes de declarar UNAVAILABLE. Com deadline menor que isso o cliente recebe DEADLINE_EXCEEDED e perde a causa real da falha. |
| status com o servidor desligado | `UNAVAILABLE` | `UNAVAILABLE` | ok | Nenhuma regra de negocio foi avaliada: a chamada nao chegou ao servico. Esse e o eixo que separa erro de aplicacao de falha de infraestrutura. |
| detalhe do UNAVAILABLE descreve o transporte | `True` | `True` | ok | details() devolveu 'failed to connect to all addresses; last error: UNAVAILABLE: ipv4:127.' — nenhuma mencao a isbn, leitor ou prazo, porque nada disso chegou a ser avaliado. |
| politica de retry sugerida para UNAVAILABLE | `repetir com backoff` | `repetir com backoff` | ok | UNAVAILABLE tende a ser transitorio, mas repetir so e seguro se a operacao for idempotente — ver E06. |
| quantidade de status distintos observados no cenario | `>= 2` | `6` | ok | A AP4 exige ao menos dois status de erro; o servico usa INVALID_ARGUMENT, NOT_FOUND, FAILED_PRECONDITION, ALREADY_EXISTS e UNAVAILABLE. |

## E03 — Deadlines de 100 ms, 1 s e 3 s no mesmo metodo

**Pergunta que o cenário responde:** Quanto tempo o cliente aceita esperar e o que o servidor faz quando ele desiste?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| deadline de 0,1 s contra trabalho de ~1,2 s | `DEADLINE_EXCEEDED` | `DEADLINE_EXCEEDED` | ok | O cliente desiste antes do servidor terminar. O status nao diz se houve efeito no servidor — so diz que o tempo acabou. |
| deadline de 1 s contra trabalho de ~1,2 s | `DEADLINE_EXCEEDED` | `DEADLINE_EXCEEDED` | ok | Um deadline plausivel ainda estoura quando o custo real supera a estimativa: o limite precisa vir do SLA, nao do otimismo. |
| deadline de 3 s contra trabalho de ~1,2 s | `OK` | `OK` | ok | Com folga suficiente a mesma chamada, o mesmo pedido e o mesmo servidor respondem normalmente. O que mudou foi so o orcamento de tempo. |
| chamada sem deadline conclui | `OK` | `OK` | ok | Sem limite a chamada termina, mas o cliente fica preso ao tempo do servidor: e exatamente o recurso bloqueado por tempo indeterminado da secao 6.5. |
| latencia observada com deadline de 0.1 s | `<= 250 ms` | `109.8` | ok | O cliente retorna proximo ao deadline, nao ao fim do trabalho: o custo de uma chamada lenta vira previsivel para quem chama. |
| latencia observada com deadline de 1 s | `<= 1150 ms` | `1016.3` | ok | O cliente retorna proximo ao deadline, nao ao fim do trabalho: o custo de uma chamada lenta vira previsivel para quem chama. |
| chamadas que o servidor abandonou por cancelamento | `2` | `2` | ok | As duas chamadas que estouraram o deadline foram interrompidas no servidor. O servidor checa context.is_active() a cada item e para de trabalhar. |
| itens processados antes de abandonar o deadline de 0,1 s | `< 40` | `4` | ok | O servidor parou em 4 de 40 itens. Trabalho que nao interessa mais ao cliente nao consome CPU ate o fim. |
| servidor enxerga o prazo restante das chamadas com deadline | `3` | `3` | ok | O deadline viaja no cabecalho da RPC. Os prazos vistos pelo servidor foram 0.10 s, 1.01 s, 3.01 s — cada um um pouco menor que o deadline do cliente, porque o tempo de rede ja foi descontado. E isso que permite propagar o orcamento de tempo para o proximo hop em vez de reiniciar o timeout. |
| chamada sem deadline chega ao servidor com prazo praticamente infinito | `1` | `1` | ok | time_remaining() devolveu 9.22e+18 s (cerca de 3e+11 anos) em vez de None. Na pratica o servidor nao tem limite e nunca cancela sozinho: o resultado pode nao interessar mais a ninguem e o trabalho continua. |

## E04 — Indisponibilidade do servidor durante o uso do cliente

**Pergunta que o cenário responde:** O cliente distingue 'o servico recusou' de 'o servico nao respondeu'?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| pedido valido com o servidor no ar | `OK` | `OK` | ok | Estado inicial do experimento. |
| pedido invalido com o servidor no ar | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | O servico recebeu, avaliou e recusou. Ha uma decisao de dominio por tras do status, e ela veio com a mensagem de erro. |
| pedido valido com o servidor fora | `UNAVAILABLE` | `UNAVAILABLE` | ok | O canal nao conseguiu entregar a chamada. Nada foi executado no servidor. |
| pedido invalido com o servidor fora | `UNAVAILABLE` | `UNAVAILABLE` | ok | O mesmo pedido que antes devolvia INVALID_ARGUMENT agora devolve UNAVAILABLE: sem servidor nao existe validacao, e a falha e do transporte. |
| UNAVAILABLE chega antes de esgotar o deadline de 5 s | `< 5000 ms` | `2041.7962999781594` | ok | O cliente nao fica preso ate o fim do deadline: ele desiste quando as tentativas de conexao falham. Mas isso leva alguns segundos, entao um deadline curto devolveria DEADLINE_EXCEEDED em vez da causa real. |
| detalhe do erro descreve transporte, nao dominio | `True` | `True` | ok | details() devolveu: 'failed to connect to all addresses; last error: UNAVAILABLE: ipv4:127.0.0.1:60126: WSAGetO' |
| chamada com wait_for_ready sobrevive a queda do servidor | `OK` | `OK` | ok | Com wait_for_ready o cliente segura a chamada ate o canal reconectar, em vez de receber UNAVAILABLE. Isso substitui o retry manual, mas so e seguro dentro do deadline e para operacoes que toleram repeticao. |
| a espera cobre o tempo que o servidor ficou fora | `> 900 ms` | `1522.3426999291405` | ok | A latencia observada inclui a janela de indisponibilidade, entao o custo da resiliencia aparece no tempo de resposta. |
| servidor morto no meio da chamada | `UNAVAILABLE` | `UNAVAILABLE` | ok | O processo foi morto com o trabalho em andamento. O cliente descobre pela queda da conexao, nao por uma resposta do servico — e nao sabe quanto do trabalho ja tinha efeito. |

## E05 — Concorrencia: max_workers do servidor contra clientes simultaneos

**Pergunta que o cenário responde:** O pool de threads do servidor limita o que o cliente enxerga como latencia?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| todas as chamadas concluem com max_workers=2 | `0` | `0` | ok | 24 chamadas de 8 clientes simultaneos; o pool estreito enfileira, mas nao derruba. |
| todas as chamadas concluem com max_workers=16 | `0` | `0` | ok | 24 chamadas com o mesmo cliente e a mesma carga. |
| p95 melhora ao aumentar max_workers | `True` | `True` | ok | p95 de 1224 ms com 2 workers contra 311 ms com 16. A fila do ThreadPoolExecutor do servidor e o gargalo, nao a rede. |
| duracao total da rodada cai com mais workers | `True` | `True` | ok | 3.67 s com 2 workers contra 0.93 s com 16. O metodo dorme por item, entao o paralelismo aparece direto no tempo total. |
| clientes simultaneos compartilham um unico canal | `8` | `8` | ok | Todas as chamadas da rodada saem do mesmo grpc.Channel: o HTTP/2 multiplexa varias RPCs na mesma conexao, diferente de uma requisicao HTTP por chamada. |
| 12 clientes disputam 1 exemplar — aceitos | `1` | `1` | ok | A reserva do exemplar acontece dentro de uma trava no repositorio, entao o paralelismo do servidor nao quebra a invariante do dominio. |
| 12 clientes disputam 1 exemplar — recusados | `11` | `11` | ok | Os demais recebem FAILED_PRECONDITION, que e um resultado de dominio e nao um erro de concorrencia vazado para o cliente. |
| emprestimos ativos do titulo com 1 exemplar | `1` | `1` | ok | A listagem confirma o estado final: nenhum emprestimo duplicado sobreviveu a corrida. |

## E06 — Retry apos deadline ambiguo, com e sem chave de idempotencia

**Pergunta que o cenário responde:** Como repetir uma chamada sem duplicar o efeito que talvez ja tenha acontecido?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| cliente desiste antes da resposta da escrita | `DEADLINE_EXCEEDED` | `DEADLINE_EXCEEDED` | ok | O deadline estourou depois que o repositorio ja tinha gravado. O cliente nao tem como saber disso pelo status. |
| servidor concluiu a chamada que o cliente deu por perdida | `>= 1` | `1` | ok | O interceptador do servidor registrou status OK para a mesma chamada que o cliente contabilizou como DEADLINE_EXCEEDED. E exatamente a ambiguidade da secao 6.10: o status nao fala sobre efeitos ja executados. |
| efeito aplicado apesar do erro visto pelo cliente | `1` | `1` | ok | Uma consulta posterior mostra o emprestimo criado: o trabalho aconteceu, so a resposta nao chegou a tempo. |
| retry sem chave duplica o emprestimo | `2` | `2` | ok | O mesmo leitor terminou com dois emprestimos do mesmo titulo e dois exemplares reservados. O retry foi seguro para a rede e destrutivo para o dominio. |
| codigos gerados no retry sem chave sao distintos | `2` | `2` | ok | Sem chave o servico nao tem como reconhecer a repeticao: cada chamada e um pedido novo. |
| primeira tentativa com chave tambem estoura o deadline | `DEADLINE_EXCEEDED` | `DEADLINE_EXCEEDED` | ok | A chave nao torna a chamada mais rapida: ela so muda o que acontece no reenvio. |
| retry com chave devolve OK | `OK` | `OK` | ok | O servico reconhece a chave e devolve o resultado da primeira execucao. |
| resposta marca que o resultado foi reaproveitado | `True` | `True` | ok | O campo reaproveitado avisa o cliente que nao houve efeito novo — informacao que um simples OK esconderia. |
| retry com chave nao duplica o emprestimo | `1` | `1` | ok | Mesmo com duas chamadas na rede, o dominio registrou um unico emprestimo. E assim que DEADLINE_EXCEEDED deixa de ser perigoso para uma operacao de escrita. |
| chave so vale para o pedido original | `ALREADY_EXISTS` | `ALREADY_EXISTS` | ok | A chave guarda a impressao do pedido. Reusar a chave com outro conteudo e bug do cliente, e o servico recusa em vez de devolver o recurso errado. |

## E07 — Evolucao do contrato: cliente antigo contra servidor novo

**Pergunta que o cenário responde:** Quais mudancas no .proto preservam clientes antigos e quais corrompem dados?

| Verificação | Esperado | Obtido | Resultado | Análise |
| --- | --- | --- | :-: | --- |
| cliente novo grava o campo adicionado na v2 | `anexo` | `anexo` | ok | Campo 5 no pedido e campo 9 na resposta, ambos ausentes no contrato anterior. |
| stubs legados nao conhecem o campo unidade | `False` | `False` | ok | Campos vistos pelo cliente antigo: codigo, devolvido_em, emprestado_em, isbn, leitor, previsto_para, situacao, titulo. |
| pedido legado tambem nao tem o campo unidade | `False` | `False` | ok | O cliente antigo nem sabe que existe o campo; ele nao e obrigado a enviar nada. |
| escrita do cliente antigo no servidor novo | `OK` | `OK` | ok | Adicionar um campo opcional nao quebra quem foi compilado antes: o servidor recebe o campo ausente com o valor padrao e aplica o default do dominio. |
| leitura do cliente antigo de um recurso criado pelo cliente novo | `OK` | `OK` | ok | A resposta traz o campo 9, que o stub antigo simplesmente ignora. |
| campos conhecidos chegam corretos ao cliente antigo | `gabriela.dias` | `gabriela.dias` | ok | Os numeros de campo nao mudaram, entao cada valor continua caindo no campo certo. |
| cliente antigo preserva o campo desconhecido ao reserializar | `True` | `True` | ok | O stub antigo guarda o campo 9 como unknown field e devolve os mesmos 86 bytes, terminados em `...4a05616e65786f` (campo 9 = 'anexo'). Um proxy compilado com o contrato velho nao apaga dados do contrato novo. |
| server streaming continua funcionando para o cliente antigo | `OK` | `OK` | ok | O fluxo entregou 2 itens usando os stubs antigos. |
| modelo de erro permanece o mesmo para o cliente antigo | `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | ok | Status e mensagens nao dependem da versao do stub: 'isbn: isbn deve ter exatamente 13 dígitos'. |
| reuso do numero de campo 4 nao gera erro de parsing | `parseou` | `parseou` | ok | Trocar leitor por unidade no campo 4 mantem o mesmo wire type, entao o parser aceita os bytes sem reclamar. |
| reuso do numero de campo 4 corrompe o dado em silencio | `gabriela.dias` | `gabriela.dias` | ok | O leitor virou unidade. Nao houve excecao, log nem status de erro: a mudanca incompativel mais perigosa e a que continua parseando. |
| troca de tipo no campo 3 tambem nao levanta excecao | `parseou` | `parseou` | ok | int32 dias virou string dias: o wire type nao bate e o valor e descartado como campo desconhecido. |
| troca de tipo no campo 3 perde o valor enviado | `` | `` | ok | O cliente enviou 7 dias e o leitor com o esquema alterado enxerga string vazia. Perda silenciosa de dado. |
| duas versoes do mesmo package no mesmo processo | `falha` | `falha` | ok | O descriptor pool do protobuf recusa simbolos duplicados: TypeError: Couldn't build proto file into descriptor pool: duplicate symbol 'biblioteca.emprestimos.. Por isso o cliente legado roda como processo separado, que e tambem como a migracao acontece na pratica. |

---

## Logs brutos

Cada processo grava uma linha JSON por evento em `logs/<id-do-processo>.jsonl`
e a saída de console em `logs/<id-do-processo>.saida.txt`. Os identificadores são
prefixados pelo código do cenário, então os arquivos de cada experimento ficam
isolados. O interceptador do servidor registra `chamada-recebida` e
`chamada-concluida` com método, status, latência e id de correlação; o
interceptador do cliente registra `resposta-recebida` com o mesmo id.
