# Fundamentos de RPC aplicados ao serviço de empréstimos

> As latências citadas vêm de uma execução registrada dos experimentos e variam entre
> execuções; [`04-evidencias.md`](04-evidencias.md) sempre traz os números mais recentes.

## 1. A ilusão de chamada local

No cliente, pedir um empréstimo se parece com uma chamada de função:

```python
resposta = stub.RegistrarEmprestimo(pedido, timeout=3.0)
```

A assinatura esconde que existe uma rede no meio. O código deste projeto torna visível cada
coisa que a função local não teria:

| O que não existe em função local | Onde aparece aqui |
| --- | --- |
| Latência | coluna *Latência* da tabela de evidências: de 1,1 ms a 2 033 ms na mesma chamada |
| Serialização | `SerializeToString()` / `ParseFromString()` nos stubs gerados |
| Falha de transporte | `UNAVAILABLE` quando o processo do servidor não está no ar |
| Tempo limite | o argumento `timeout=`, que vira um deadline no cabeçalho da RPC |
| Efeito incerto | `DEADLINE_EXCEEDED` depois de o servidor já ter gravado (E06) |

O experimento E06 é o que fecha o argumento: o cliente recebeu `DEADLINE_EXCEEDED` e o
servidor registrou `OK` **para a mesma chamada**. Uma função local não tem esse estado
intermediário — ou ela retornou, ou levantou exceção.

## 2. IDL e geração de stubs

O contrato é escrito primeiro, em [`contratos/emprestimos.proto`](../contratos/emprestimos.proto),
e o código dos dois lados é gerado a partir dele por [`gerar_stubs.py`](../gerar_stubs.py):

```text
contratos/emprestimos.proto
        │  python -m grpc_tools.protoc
        ├─► contratos/emprestimos_pb2.py       mensagens (marshalling)
        ├─► contratos/emprestimos_pb2.pyi      tipos para o editor
        └─► contratos/emprestimos_pb2_grpc.py  stub do cliente + servicer do servidor
```

O script apaga os arquivos gerados antes de chamar o `protoc`, então a regeneração é do zero.
O experimento E01 compara o SHA-256 de cada arquivo antes e depois: são idênticos, o que prova
que nada no código gerado foi editado à mão.

A consequência prática da IDL é a inversão de quem define a verdade. Em REST, o contrato é
documentação sobre um formato de texto; aqui, o contrato *é* o código. Um campo com o nome
errado não passa em tempo de escrita, não em tempo de execução.

## 3. Marshalling: o que viaja no fio

Protocol Buffers não envia nomes de campo. Envia pares *(número do campo, wire type)* seguidos
do valor. O empréstimo abaixo, com 86 bytes, foi capturado no E07 (campos 3, 5 e 6 omitidos
aqui por brevidade):

```text
0a 08 45 4d 50 2d 30 30 30 31   campo 1 (codigo), string, 8 bytes: "EMP-0001"
12 0d 39 37 38 38 ...           campo 2 (isbn), string, 13 bytes
22 0d 67 61 62 72 ...           campo 4 (leitor), string, 13 bytes: "gabriela.dias"
40 01                           campo 8 (situacao), varint: 1 = SITUACAO_ATIVO
4a 05 61 6e 65 78 6f            campo 9 (unidade), string, 5 bytes: "anexo"
```

Três consequências que os experimentos confirmam:

- **O número do campo é a identidade.** Renomear `leitor` para `unidade` mantendo o número 4
  não muda um byte no fio — e por isso corrompe o dado em silêncio (E07).
- **Campo ausente não é distinguível de campo com valor padrão.** Em proto3, `dias = 0` e
  `dias` não enviado produzem os mesmos bytes. Por isso o serviço trata `dias == 0` como
  "use o prazo padrão" em vez de rejeitar, e a obrigatoriedade de `codigos` em
  `CalcularMultas` é regra de serviço, não do contrato.
- **O que o leitor não conhece ele guarda.** O cliente legado do E07 desserializou e
  reserializou o empréstimo acima e devolveu os mesmos 86 bytes, com o campo 9 intacto.

## 4. Tipos de RPC

| Tipo | Uso neste projeto |
| --- | --- |
| Unary | `RegistrarEmprestimo`, `ConsultarEmprestimo`, `RegistrarDevolucao`, `CalcularMultas` |
| Server streaming | `ListarEmprestimos` — uma requisição, um fluxo de `Emprestimo` |
| Client streaming | não usado; caberia em uma carga de devoluções em lote |
| Bidirectional | não usado; caberia em um terminal de autoatendimento interativo |

`ListarEmprestimos` entrega quatro empréstimos em uma única RPC (E01). A alternativa sem
streaming seria uma RPC por item ou uma resposta única com tudo dentro — a primeira paga
overhead por item, a segunda obriga o servidor a materializar a lista inteira antes de
responder.

O custo do streaming é manter recursos ocupados por mais tempo: a thread do servidor só é
liberada quando o gerador termina. Por isso `ListarEmprestimos` checa `context.is_active()`
a cada item e para de produzir se o cliente sumiu.

## 5. Deadlines, cancelamento e orçamento de tempo

O deadline não é um timeout local do cliente: ele viaja no cabeçalho da RPC. O interceptador
do servidor registra `context.time_remaining()` na chegada de cada chamada, e o E03 mostra os
valores:

| Deadline pedido pelo cliente | Prazo visto pelo servidor |
| --- | --- |
| 0,1 s | 0,093 s |
| 1 s | 1,008 s |
| 3 s | 3,008 s |
| nenhum | 9,2 × 10¹⁸ s |

Dois pontos:

- O servidor recebe um prazo **menor** que o do cliente quando o tempo de rede já pesa. É esse
  valor que deve ser propagado para o próximo hop — se cada serviço da cadeia reiniciar o
  timeout completo, o SLA total vira a soma dos timeouts, não o maior deles.
- Sem deadline, `time_remaining()` não devolve `None`: devolve o maior int64 em nanossegundos,
  cerca de 2,9 × 10¹¹ anos. Na prática o servidor nunca cancela sozinho.

O cancelamento é observável dos dois lados. Com deadline de 0,1 s contra um trabalho de 1,2 s,
o servidor processou 4 dos 40 itens e abandonou a chamada. O trabalho que não interessa mais a
ninguém não consome CPU até o fim — mas isso só acontece porque o método **verifica**; um
laço que ignora `is_active()` terminaria os 40.

## 6. Modelo de erro

O serviço levanta erros de domínio (`EntradaInvalida`, `NaoEncontrado`, `PrecondicaoFalhou`,
`JaExiste`) e um único ponto — o interceptador do servidor — traduz cada categoria para um
status gRPC:

| Erro de domínio | Status | Significado para o cliente |
| --- | --- | --- |
| `EntradaInvalida` | `INVALID_ARGUMENT` | o pedido está errado, independentemente do estado |
| `NaoEncontrado` | `NOT_FOUND` | o pedido está certo, a entidade não existe |
| `PrecondicaoFalhou` | `FAILED_PRECONDITION` | o estado atual impede a operação |
| `JaExiste` | `ALREADY_EXISTS` | a chave de idempotência já foi usada com outro pedido |
| — | `UNAVAILABLE` | a chamada não chegou ao serviço |
| — | `DEADLINE_EXCEEDED` | o tempo acabou; o efeito é desconhecido |

Cada status carrega uma política de retry (`app/erros.py`), e o cliente pode decidir sem ler
a mensagem de erro:

| Status | Política |
| --- | --- |
| `UNAVAILABLE` | repetir com backoff |
| `INVALID_ARGUMENT`, `NOT_FOUND`, `FAILED_PRECONDITION`, `ALREADY_EXISTS` | corrigir a chamada, nunca repetir |
| `DEADLINE_EXCEEDED`, `CANCELLED` | repetir apenas com chave de idempotência |

Além do status, o serviço devolve `x-campo` no *trailing metadata* apontando qual campo
falhou. O cliente sabe o que corrigir sem fazer parsing da mensagem em português.

## 7. Interceptors

Duas preocupações transversais ficam fora dos métodos de negócio:

- **Servidor** (`InterceptadorDoServidor`): mede latência, registra `chamada-recebida` e
  `chamada-concluida` em JSON, e traduz erro de domínio em status gRPC.
- **Cliente** (`InterceptadorDoCliente`): injeta `x-correlacao-id` quando não existe e registra
  `resposta-recebida` com o mesmo id.

Com isso, uma chamada pode ser seguida do cliente ao servidor pelo id de correlação, e
`ServicoDeEmprestimos` não importa `grpc` para nada além dos tipos gerados — ele levanta
exceções de domínio e não sabe que existe um código de status.

O limite que a apostila aponta vale aqui: o interceptador faz observabilidade e tradução, que
são transversais. A decisão de recusar um empréstimo sem exemplar continua no serviço, visível
e testável.

## 8. Segurança

O laboratório usa `insecure_channel`, como o exemplo da apostila. O que estaria faltando em
produção, e onde entraria neste código:

| Preocupação | Onde |
| --- | --- |
| TLS | `add_secure_port` no lugar de `add_insecure_port`, com `ssl_channel_credentials` no cliente |
| Autenticação | metadata de credencial validada em um interceptador, antes do serviço |
| Autorização por método | `handler_call_details.method` já está disponível no interceptador |
| Tamanho de mensagem | já limitado a 4 MiB nas duas pontas (`OPCOES_DO_CANAL`) |
| Limite de concorrência | já limitado por `maximum_concurrent_rpcs=64` e pelo `max_workers` |
| Exposição de metadados | `x-campo` devolve o nome do campo, nunca o valor recebido |
