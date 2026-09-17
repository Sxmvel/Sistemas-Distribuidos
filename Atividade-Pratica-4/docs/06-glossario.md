# Glossário

Termos usados no código e nos demais documentos desta atividade.

## Protocolo e contrato

**IDL (Interface Definition Language).** Linguagem para descrever a interface de um serviço
independentemente da linguagem de programação. Aqui, o arquivo `.proto`.

**Protocol Buffers.** Formato de serialização binária da Google e a IDL que o acompanha. No fio
envia pares *(número do campo, wire type)* e valor — nunca o nome do campo.

**Stub.** Código gerado que dá ao cliente a aparência de uma chamada local. O lado do servidor
equivalente é o *servicer*, a classe base que o serviço implementa.

**Marshalling.** Converter estruturas de memória em bytes para transmissão (e o inverso,
*unmarshalling*). Nos stubs gerados: `SerializeToString()` e `ParseFromString()`.

**Wire type.** Como o valor de um campo é codificado: varint, 64 bits, *length-delimited*,
32 bits. Determina se uma troca de tipo quebra o parsing ou passa silenciosamente.

**Campo desconhecido (*unknown field*).** Campo presente nos bytes mas ausente no esquema de
quem lê. O protobuf o guarda e o devolve ao reserializar, o que permite que um intermediário
antigo não apague dados de um contrato mais novo.

**`reserved`.** Declaração que proíbe reutilizar um número ou nome de campo removido.

**Descriptor pool.** Registro global de tipos protobuf de um processo, indexado pelo nome
completo (`biblioteca.emprestimos.v1.Emprestimo`). Recusa símbolos duplicados, o que impede
duas versões do mesmo `package` no mesmo processo.

## Tipos de RPC

**Unary.** Uma requisição, uma resposta.

**Server streaming.** Uma requisição, um fluxo de respostas. Aqui, `ListarEmprestimos`.

**Client streaming.** Um fluxo de requisições, uma resposta.

**Bidirectional streaming.** Os dois lados enviam fluxos independentes.

## Tempo e falhas

**Deadline.** Instante a partir do qual o cliente deixa de aceitar a resposta. Viaja no
cabeçalho da RPC, então o servidor também o enxerga via `context.time_remaining()`.

**Timeout.** Duração. Vira um deadline quando somada ao instante da chamada. No código, o
argumento `timeout=` de cada chamada.

**Orçamento de tempo.** O deadline restante que um serviço deve repassar ao próximo ao compor
chamadas. Reiniciar o timeout em cada hop faz o SLA total virar a soma dos timeouts.

**Cancelamento.** Sinal de que o cliente não quer mais o resultado. O servidor o observa com
`context.is_active()` e pode interromper o trabalho.

**`wait_for_ready`.** Opção que faz a chamada esperar o canal reconectar em vez de falhar com
`UNAVAILABLE`. Troca falha rápida por latência.

**Falha rápida (*fail fast*).** Comportamento padrão do gRPC: quando o canal sabe que o destino
está indisponível, a chamada falha imediatamente em vez de esperar o deadline.

## Status gRPC usados

| Status | Significado neste serviço |
| --- | --- |
| `OK` | a chamada foi processada |
| `INVALID_ARGUMENT` | o pedido está mal formado, independentemente do estado |
| `NOT_FOUND` | o pedido está correto, a entidade não existe |
| `FAILED_PRECONDITION` | o estado atual impede a operação |
| `ALREADY_EXISTS` | a chave de idempotência já foi usada com outro pedido |
| `UNAVAILABLE` | a chamada não chegou ao serviço |
| `DEADLINE_EXCEEDED` | o tempo acabou; o efeito no servidor é desconhecido |
| `CANCELLED` | o cliente desistiu explicitamente |

## Confiabilidade

**Idempotência.** Propriedade de uma operação cujo efeito de N execuções é igual ao de uma.
`ConsultarEmprestimo` é idempotente por natureza; `RegistrarEmprestimo` só é com chave.

**Chave de idempotência.** Identificador escolhido pelo cliente que permite ao servidor
reconhecer um reenvio. Aqui, o campo `chave_idempotencia`, guardado com uma impressão do
pedido.

**Efeito ambíguo.** Situação em que o cliente não sabe se a operação teve efeito. É o que
`DEADLINE_EXCEEDED` e a queda de conexão produzem.

**Backoff com jitter.** Espera crescente e aleatorizada entre tentativas, para não sincronizar
todos os clientes no mesmo instante.

## Observabilidade e infraestrutura

**Interceptor.** Ponto de extensão que envolve cada chamada, para logging, métricas,
autenticação ou tradução de erros, sem repetir código em cada método.

**Id de correlação.** Identificador que acompanha uma chamada pelas duas pontas. Aqui viaja no
metadado `x-correlacao-id`, injetado pelo interceptador do cliente.

**Metadados.** Pares chave/valor que acompanham a chamada, análogos a cabeçalhos HTTP.
*Trailing metadata* vem junto com o status final — é onde o serviço devolve `x-campo`.

**`max_workers`.** Tamanho do pool de threads que atende as chamadas. Limita quantas RPCs são
processadas em paralelo; o E05 mede o efeito no p95.

**`maximum_concurrent_rpcs`.** Teto de chamadas simultâneas aceitas pelo servidor. Acima dele,
novas chamadas são recusadas em vez de enfileiradas indefinidamente.

**Multiplexação HTTP/2.** Várias RPCs simultâneas em uma única conexão TCP. É por isso que os
oito clientes concorrentes do E05 compartilham um único `grpc.Channel`.

**Liveness / readiness.** *Liveness* é "o processo está vivo"; *readiness* é "está apto a
receber tráfego". Um processo vivo pode estar sem acesso a uma dependência crítica — o E04
mostra o caso extremo, com o processo morto no meio de uma chamada.

## Domínio

**Empréstimo.** Associação entre um exemplar de um livro e um leitor, com data prevista de
devolução. Identificado por um código `EMP-NNNN`.

**Exemplar.** Cópia física de um título. O acervo define quantos existem de cada ISBN, e a
contagem de empréstimos ativos determina a disponibilidade.

**Multa.** `dias de atraso × R$ 0,50`, calculada contra uma data de referência.

**Unidade.** Filial da biblioteca (`central` ou `anexo`). Foi o campo adicionado na v2 do
contrato e usado para demonstrar evolução compatível.
