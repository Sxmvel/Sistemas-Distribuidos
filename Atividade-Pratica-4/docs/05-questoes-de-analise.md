# Questões de análise

As respostas citam as evidências de [`04-evidencias.md`](04-evidencias.md), geradas pela
execução dos sete experimentos.

> As latências são de uma execução registrada (Python 3.14.3, grpcio 1.84.0, Windows) e
> variam alguns por cento entre execuções. O que não varia é a ordem de grandeza e a relação
> entre os casos, que é o que cada comparação abaixo usa. O arquivo de evidências sempre traz
> os números da última execução.

## 1. Por que uma chamada remota não deve ser tratada como função local?

Porque a assinatura é a mesma, mas o conjunto de resultados possíveis não é. Uma função local
retorna ou levanta exceção. Uma chamada remota tem um terceiro resultado: **não se sabe**.

O E06 produz exatamente esse caso. O cliente chamou `RegistrarEmprestimo` com deadline de
150 ms contra um servidor que leva 500 ms para responder a escrita:

- o cliente registrou `DEADLINE_EXCEEDED` em 153,8 ms;
- o interceptador do servidor registrou `OK` para a mesma chamada;
- uma consulta posterior mostrou o empréstimo **criado**.

Não existe nenhuma informação no status que distinga "não aconteceu" de "aconteceu e a
resposta se perdeu". Quem escreveu o cliente precisa decidir o que fazer com essa dúvida, e
essa decisão não existe em código local.

As outras diferenças aparecem em números na tabela de latência:

- **Latência varia três ordens de grandeza.** A mesma `RegistrarEmprestimo` custou 1,1 ms com
  o canal quente, 274 ms na primeira chamada do processo (handshake HTTP/2) e 2 033 ms quando
  o servidor estava fora e o gRPC tentou reconectar.
- **Os argumentos são copiados, não compartilhados.** O `Emprestimo` que o cliente recebe é
  uma reconstrução a partir de 86 bytes; qualquer coisa que não esteja no `.proto` não
  atravessa.
- **O servidor pode desaparecer no meio.** O E04 matou o processo durante uma chamada de
  ~1,8 s e o cliente recebeu `UNAVAILABLE` em 605,9 ms.
- **O tempo é finito por contrato.** Sem `timeout`, o servidor recebe um prazo de
  9,2 × 10¹⁸ s e nunca cancela nada.

## 2. Qual diferença entre erro de aplicação e indisponibilidade do serviço?

**Erro de aplicação** significa que a chamada chegou, foi avaliada e foi recusada por uma
decisão do serviço. **Indisponibilidade** significa que nenhuma decisão foi tomada, porque
a chamada não chegou.

O E04 isola essa diferença usando o mesmo pedido inválido duas vezes:

| Estado do servidor | Pedido | Status | Latência |
| --- | --- | --- | --- |
| no ar | `isbn = "123"` | `INVALID_ARGUMENT` | 1,9 ms |
| fora | `isbn = "123"` | `UNAVAILABLE` | 0,8 ms |

O pedido é idêntico. O que mudou foi apenas a existência do servidor — e com ela o eixo do
erro: no primeiro caso o problema é do chamador, no segundo é da infraestrutura.

Três consequências práticas:

- **A ação é diferente.** `INVALID_ARGUMENT` exige corrigir o código do cliente; repetir é
  desperdício garantido. `UNAVAILABLE` tende a ser transitório e admite retry com backoff.
- **O responsável é diferente.** Um pico de `INVALID_ARGUMENT` é bug de quem chama. Um pico de
  `UNAVAILABLE` é incidente de operação.
- **O conteúdo do erro é diferente.** `INVALID_ARGUMENT` veio com
  `isbn: isbn deve ter exatamente 13 dígitos` e `x-campo: isbn`. `UNAVAILABLE` veio com
  `failed to connect to all addresses` — nenhuma menção ao domínio, porque nada do domínio
  foi executado.

Há uma armadilha medida no E02: num canal recém-aberto, o gRPC leva cerca de 2 s tentando
conectar antes de declarar `UNAVAILABLE`. Com deadline de 1,5 s, o cliente recebeu
`DEADLINE_EXCEEDED` (1 512 ms); com 5 s, recebeu `UNAVAILABLE` (548 ms). **Um deadline curto
demais esconde a indisponibilidade atrás de um timeout** e leva a diagnóstico errado. Vale
notar o contraste com a linha de 0,8 ms acima: quando o canal já sabe que o servidor caiu, a
falha é imediata; o custo dos 2 s é o da primeira descoberta.

`FAILED_PRECONDITION` é o terceiro caso, e não cabe em nenhum dos dois: o pedido está certo e
o serviço está no ar, mas o estado impede a operação. No E02, o segundo empréstimo de um
título com um único exemplar recebeu `FAILED_PRECONDITION` — repetir não adianta enquanto
ninguém devolver o livro.

## 3. O contrato forte aumenta qual tipo de acoplamento?

Acoplamento **de esquema** — e, por consequência, acoplamento de ciclo de vida de build.

Cliente e servidor não compartilham apenas um formato de dados: compartilham um artefato
gerado a partir da mesma fonte. O que isso implica na prática, medido no E07:

- **Acoplamento ao arquivo, não ao serviço no ar.** Mudar o `.proto` obriga a regenerar e
  reimplantar quem consome. Não existe "descobrir o novo campo em tempo de execução": o
  cliente legado não tem `unidade` na lista de campos do seu `Emprestimo` e não teria como
  passar a ter sem recompilar.
- **Acoplamento ao número do campo, não ao nome.** No fio não existe nome. A identidade é o
  número, e é por isso que a evolução exige disciplina: reaproveitar o número 4 fez `unidade`
  valer `"gabriela.dias"` sem erro nenhum.
- **Acoplamento ao caminho completo.** O método viaja como
  `/biblioteca.emprestimos.v1.Emprestimos/RegistrarEmprestimo`. Renomear pacote, serviço ou
  método quebra todo cliente existente.
- **Acoplamento de toolchain.** As três versões do contrato declaram o mesmo `package` e o
  descriptor pool recusa carregá-las no mesmo processo. Conviver com duas versões do esquema
  exige dois processos, ou pacotes distintos.

Em troca, o contrato forte **reduz** acoplamento semântico implícito: não há discussão sobre
se `dias` é número ou string, se a data vem em ISO ou em `dd/mm/aaaa`, ou se um campo ausente
é `null` ou vazio. O `.proto` é a resposta, e ela é a mesma nas duas pontas.

O que o contrato forte **não** resolve: ele garante forma, não regra. `int32 dias` aceita
`-1` e `99`; quem recusa é `validar_dias`. `repeated string codigos` aceita lista vazia; quem
recusa é o serviço. `string leitor` aceita `"Ana Souza"`; quem recusa é `validar_leitor`. Os
oito casos de `INVALID_ARGUMENT` do E02 são todos de pedidos que o contrato aprovou.

## 4. Como você faria retry sem duplicar efeitos perigosos?

Com uma **chave de idempotência escolhida pelo cliente**, guardada no servidor junto com uma
impressão do pedido. É o que o campo `chave_idempotencia` faz, e o E06 mede os dois caminhos.

### Sem chave

| Passo | Resultado |
| --- | --- |
| 1ª tentativa, deadline 150 ms | `DEADLINE_EXCEEDED` em 153,8 ms |
| efeito no servidor | empréstimo criado |
| retry do mesmo pedido | `OK` em 510,8 ms |
| estado final | **2 empréstimos**, códigos distintos, 2 exemplares reservados |

### Com chave

| Passo | Resultado |
| --- | --- |
| 1ª tentativa, deadline 150 ms | `DEADLINE_EXCEEDED` em 160,2 ms |
| retry com a mesma chave | `OK`, `reaproveitado = true` |
| estado final | **1 empréstimo** |

O retry foi seguro para a rede nos dois casos. Só no segundo ele foi seguro para o domínio.

### A política completa

O cliente decide a partir do status, sem ler a mensagem de erro (`app/erros.py`):

| Status | Política | Por quê |
| --- | --- | --- |
| `UNAVAILABLE` | repetir com backoff e jitter | a chamada não chegou; não há efeito a duplicar |
| `DEADLINE_EXCEEDED`, `CANCELLED` | repetir **apenas** com chave de idempotência | o efeito é desconhecido |
| `INVALID_ARGUMENT`, `NOT_FOUND`, `FAILED_PRECONDITION`, `ALREADY_EXISTS` | nunca repetir | o resultado não muda sem mudar a chamada ou o estado |

Quatro detalhes que fazem a diferença entre uma chave que funciona e uma que dá falsa
segurança:

1. **A chave é do cliente, não do servidor.** Se o servidor gerasse a chave, ela viria na
   resposta — que é justamente o que se perdeu.
2. **A chave guarda a impressão do pedido.** Reusar a mesma chave com outro conteúdo devolve
   `ALREADY_EXISTS` em vez de devolver silenciosamente o empréstimo errado. No E06, mudar o
   leitor mantendo a chave foi recusado.
3. **A resposta diz que houve reaproveitamento.** O campo `reaproveitado` distingue "criei
   agora" de "já existia". Um `OK` puro esconderia essa diferença.
4. **A gravação e o registro da chave acontecem sob a mesma trava.** Sem isso, dois retries
   simultâneos poderiam passar pela verificação antes de qualquer um gravar.

Nem toda operação precisa disso. `ConsultarEmprestimo` e `ListarEmprestimos` são leituras:
repetir é sempre seguro. `RegistrarDevolucao` é naturalmente detectável — a segunda devolução
devolve `FAILED_PRECONDITION` porque o empréstimo já tem data. Só `RegistrarEmprestimo`
precisou de chave, porque duas chamadas iguais são um pedido legítimo de dois empréstimos.

Uma alternativa parcial aparece no E04: `wait_for_ready=True` faz o cliente segurar a chamada
até o canal reconectar em vez de receber `UNAVAILABLE` — a chamada sobreviveu à queda e voltou
`OK` em 1 538 ms. Isso evita o retry manual, mas não resolve a ambiguidade do deadline: se o
tempo acabar, a dúvida continua.

## 5. Que mudança no `.proto` seria incompatível?

O E07 mede duas, e o resultado é pior do que quebrar: **nenhuma das duas levanta erro**.

| Mudança | Bytes v2 lidos com o esquema alterado |
| --- | --- |
| Campo 4 deixa de ser `leitor` e passa a ser `unidade` (mesmo tipo `string`) | parseia sem erro; `unidade` vale `"gabriela.dias"` |
| Campo 3 muda de `int32 dias` para `string dias` | parseia sem erro; `dias` vale `""`, e o valor 7 enviado desaparece |

A primeira corrompe o dado, a segunda o perde, e as duas passam por qualquer teste que só
verifique "a chamada respondeu". Esse é o ponto central: em Protocol Buffers o parser casa
*número de campo*, não nome. Trocar o significado de um número é invisível no fio.

Lista das mudanças incompatíveis, com o motivo:

| Mudança | Por quê quebra |
| --- | --- |
| Reutilizar o número de um campo removido | bytes antigos ainda circulam e passam a ser lidos como outra coisa |
| Mudar o tipo de um campo existente | se o wire type mudar, o valor é descartado; se não mudar, é reinterpretado |
| Mudar `repeated` para singular ou vice-versa | a cardinalidade muda como o parser trata ocorrências repetidas |
| Renomear ou renumerar valores de enum | o número é o que viaja; o cliente antigo mapeia para o símbolo errado |
| Renomear pacote, serviço ou método | muda o caminho da RPC; o servidor devolve `UNIMPLEMENTED` |
| Tornar obrigatório algo que era opcional | proto3 não tem `required`, então isso vira validação de serviço — e passa a rejeitar clientes antigos que não enviam o campo |

Foi para prevenir o primeiro caso que `Emprestimo` declara `reserved 15;` e
`reserved "telefone_do_leitor";`: o `protoc` passa a recusar qualquer tentativa futura de
reaproveitar o número ou o nome.

A mudança **compatível** feita nesta atividade foi adicionar `unidade` com números novos
(5 no pedido, 9 na resposta). O E07 confirma que o cliente legado escreve, lê, recebe stream,
recebe os mesmos status de erro e ainda preserva o campo desconhecido ao reserializar.

---

## Análise comparativa: gRPC, a AP2 (REST) e a AP3 (MQTT)

As três atividades modelam o **mesmo domínio** — o acervo e os empréstimos de uma biblioteca —
com três estilos de comunicação. Isso torna a comparação direta: o que muda é o estilo, não o
problema.

| | AP2 — REST/HTTP | AP3 — MQTT | AP4 — gRPC |
| --- | --- | --- | --- |
| Estilo | requisição/resposta sobre recursos | publish/subscribe por tópicos | chamada de procedimento |
| Contrato | OpenAPI, descritivo e opcional | tópico + envelope JSON versionado | `.proto`, prescritivo e obrigatório |
| Formato | JSON, texto, autodescritivo | JSON, texto, autodescritivo | Protobuf, binário, sem nomes no fio |
| Acoplamento | de recurso e de formato | de tópico e de envelope | de esquema e de build |
| Acoplamento temporal | síncrono | assíncrono, o broker desacopla | síncrono |
| Quem conhece quem | cliente conhece a URL | nenhum lado conhece o outro | cliente conhece o endereço e o método |
| Erros | status HTTP + corpo de erro | nenhum canal de erro; só tópico de status | status gRPC + details + trailing metadata |
| Entrega | por requisição | QoS 0/1/2 do broker | por RPC |
| Concorrência | uma conexão por requisição (com keep-alive) | sessão persistente com o broker | HTTP/2 multiplexa RPCs em uma conexão |

### O que cada estilo torna fácil

**REST (AP2)** torna fácil ser genérico. Qualquer cliente com um cliente HTTP consegue
consumir a API, e o JSON é legível sem ferramenta. A AP2 explorou o que o HTTP já oferece
como vocabulário: `ETag`/`If-Match` para concorrência otimista, paginação por `pagina` e
`tamanho` na query string, e a semântica de `GET`/`PUT`/`DELETE` como contrato de
idempotência. A parte que veio de graça foi a semântica dos verbos e dos cabeçalhos
condicionais; o resto continuou sendo convenção da aplicação.

**MQTT (AP3)** torna fácil desacoplar. O terminal de autoatendimento publica um empréstimo sem
saber que existem um painel de acervo e um serviço de atrasos. Adicionar um terceiro consumidor
não toca em uma linha do publicador. O broker também absorve indisponibilidade: com QoS 1 e
sessão persistente, a AP3 mediu zero mensagens perdidas durante uma queda de 3 s do broker,
enquanto QoS 0 perdeu o que foi produzido na janela.

**gRPC (AP4)** torna fácil ser preciso. O contrato é executável, os tipos são verificados na
geração, o status de erro é padronizado e o deadline é parte do protocolo, não uma convenção.
O experimento E03 mostra algo que nem REST nem MQTT oferecem de fábrica: o servidor **enxerga**
o prazo restante do cliente e interrompe o trabalho quando ele desiste — 4 de 40 itens
processados em vez de 40.

### O que cada estilo torna difícil

**REST.** O contrato é documentação. Se o servidor passar a devolver `dias` como string,
nada quebra na geração — quebra em produção, no cliente, em runtime. A AP2 precisou de uma
suíte de testes de invariantes de contrato justamente para cobrir o que o `.proto` cobre de
graça aqui.

**MQTT.** Não existe resposta. A AP3 teve de construir à mão o que a AP4 recebe pronto:
deduplicação por `message_id` (porque QoS 1 é *pelo menos uma vez*), um envelope versionado
para evoluir o formato, e um tópico de status separado porque não há canal de erro. Perguntar
"quantos exemplares restam?" não tem forma natural em pub/sub — é preciso inventar um tópico
de requisição e um de resposta, reconstruindo RPC por cima.

**gRPC.** O acoplamento de build é real. Um `curl` não consegue chamar o serviço; é preciso
gerar stubs. O binário não é legível em log sem ferramenta. E a evolução, como o E07 mostra,
tem armadilhas silenciosas que texto autodescritivo não tem: em JSON, renomear um campo dá
`null`; em Protobuf, reaproveitar um número dá o valor errado sem aviso.

### Idempotência: três soluções para o mesmo problema

O problema é o mesmo nas três atividades — repetir uma operação sem duplicar o efeito — e
cada estilo o resolve em um nível diferente:

| | Onde mora a solução |
| --- | --- |
| AP2 | no **protocolo**: `PUT` é idempotente por definição de HTTP; `If-Match` com `ETag` recusa a escrita se o recurso mudou |
| AP3 | na **mensagem**: `message_id` no envelope, e cada consumidor mantém a sua tabela de deduplicação |
| AP4 | na **aplicação**: campo `chave_idempotencia` no pedido, guardado com a impressão do pedido |

gRPC é o que menos ajuda aqui. Não existe um "método idempotente" no protocolo — todo RPC é
uma chamada opaca. A ambiguidade do `DEADLINE_EXCEEDED` é a mesma de um `POST` HTTP que deu
timeout, mas o HTTP ao menos oferece verbos com semântica combinada.

### Quando escolher cada um, neste domínio

- **REST** para a API pública do catálogo: leitura por terceiros, cacheável, consumível por
  qualquer front-end sem toolchain.
- **MQTT** para os eventos do acervo: "livro emprestado", "livro devolvido", "terminal
  offline". Muitos interessados, nenhum precisa de resposta, e o publicador não deve saber
  quem escuta.
- **gRPC** para a comunicação entre serviços internos: o terminal chamando o serviço de
  empréstimos, onde importa contrato forte, baixa latência, deadline propagado e um erro que
  diz exatamente o que houve.

A conclusão prática das três atividades é que eles não competem. Um sistema real de biblioteca
usaria os três: REST na borda, gRPC entre serviços, MQTT para propagar o que aconteceu.
