# Questões de análise

## 1. Quais operações são idempotentes e por quê?

Uma operação é idempotente quando executá-la uma vez ou N vezes leva ao mesmo estado final do
recurso. A propriedade descreve o **efeito sobre o estado**, não a resposta devolvida.

| Operação | Idempotente | Por quê |
| --- | :-: | --- |
| `GET /v1/livros` | sim | é segura: não altera estado nenhum |
| `GET /v1/livros/{id}` | sim | idem |
| `POST /v1/livros` | **não** | cada chamada cria um recurso novo, com id novo |
| `POST /v1/livros/{id}/emprestimos` | **não** | cada chamada registra um empréstimo distinto |
| `PUT /v1/livros/{id}` | sim | substitui a representação inteira pelo corpo enviado |
| `PATCH /v1/livros/{id}` | sim | aplica valores absolutos, não incrementos |
| `DELETE /v1/livros/{id}` | sim quanto ao efeito | o recurso fica ausente em qualquer repetição |

### Por que POST não é idempotente

O identificador é gerado pelo servidor. Duas requisições idênticas produzem dois recursos
diferentes, em URIs diferentes. É o comportamento correto para criação: se o cliente reenvia
por não ter recebido resposta, ele acaba com dois cadastros. Evidência em
`C05 → POST /v1/livros repetido`.

Para tornar a criação segura contra reenvio seria preciso uma chave de idempotência fornecida
pelo cliente (`Idempotency-Key`), armazenada pelo servidor junto com a resposta original. Não
foi implementado aqui, e essa ausência é o motivo pelo qual repetir um `POST` após um timeout
é arriscado.

### Por que DELETE é idempotente mesmo mudando de status

```
DELETE /v1/livros/18  →  204 No Content    (recurso removido)
DELETE /v1/livros/18  →  404 Not Found     (recurso continua ausente)
```

O status muda porque a segunda resposta descreve honestamente o que o servidor encontrou.
O estado final, porém, é idêntico nos dois casos: o livro 18 não existe. Idempotência é sobre
o estado resultante, não sobre a resposta. Evidência em `C05` e em
`testes/test_invariantes.py::test_delete_repetido_mantem_o_mesmo_estado_final`.

### A decisão que tornou PUT verdadeiramente idempotente

O repositório compara os valores enviados com os atuais e **só incrementa `versao` quando algo
muda de fato**:

```python
if tuple(atual) != novos_valores:
    conn.execute("UPDATE livros SET ..., versao = versao + 1 WHERE id = ?", ...)
```

Sem essa comparação, um `PUT` idêntico repetido devolveria o mesmo conteúdo, mas com `ETag`
diferente a cada chamada — e o campo `versao`, que aparece no corpo, também mudaria. A
idempotência estaria quebrada de um ponto de vista observável, mesmo que os campos de domínio
permanecessem iguais. Evidência em `C05 → ETag após o PUT repetido`.

### Por que PATCH é idempotente nesta API

Não por natureza do método, mas por decisão de contrato: os campos aceitos carregam valores
absolutos. Se o `PATCH` aceitasse algo como `{"acrescentar_exemplares": 1}`, cada repetição
produziria um resultado diferente e o método deixaria de ser idempotente. A apostila registra
"depende da operação" justamente por isso.

---

## 2. Que diferença existe entre "servidor respondeu erro" e "cliente não conseguiu obter resposta"?

A diferença é **a existência de informação**.

| | Servidor respondeu erro | Cliente não obteve resposta |
| --- | --- | --- |
| Exemplo | `503 Service Unavailable` | `ConnectionError`, `Timeout` |
| Houve mensagem HTTP? | sim | não |
| O cliente sabe o que aconteceu? | sim, o servidor declarou | não |
| A operação foi executada? | o status informa | **desconhecido** |
| Repetir é seguro? | decidível a partir do status | depende do método |

Evidência em `C08`: `GET http://127.0.0.1:65000/v1/livros` produz `ConnectionError`, enquanto
`GET /v1/indisponivel` produz `503` com `Retry-After: 5`.

### Por que a distinção é o problema central de sistemas distribuídos

Quando o servidor responde `503`, ele **participou da conversa**. Ele afirma: recebi sua
requisição, estou indisponível agora, tente de novo em 5 segundos. O cliente tem informação
suficiente para decidir.

Quando ocorre `ConnectionError` ou `Timeout`, o cliente tem apenas ausência de informação. As
possibilidades são indistinguíveis do lado dele:

1. a requisição nunca chegou ao servidor;
2. chegou, o servidor processou por completo, e a resposta se perdeu no caminho;
3. chegou, e o servidor ainda está processando neste momento.

No caso 1 repetir é obrigatório. No caso 2 repetir duplica o efeito. No caso 3 repetir pode
gerar concorrência com a própria requisição anterior. **E o cliente não tem como saber em qual
caso está.**

É por isso que o `C07` observa a mesma rota com três timeouts diferentes: com `timeout=0.5`
o cliente desiste enquanto o servidor conclui normalmente. A chamada remota não tem duração
garantida, e o timeout é uma decisão do cliente sobre quanto tempo aceita esperar — não uma
propriedade do servidor.

### Consequência prática

Repetir automaticamente só é seguro em operações idempotentes. `GET`, `PUT` e `DELETE` podem
ser reenviados sem risco. `POST` não: um empréstimo pode ser registrado duas vezes. Para
tornar o reenvio de `POST` seguro seria necessária uma chave de idempotência, conforme
discutido na questão 1.

---

## 3. Que decisões da sua API aumentam ou reduzem acoplamento entre cliente e servidor?

### Decisões que reduzem acoplamento

**`Location` nas respostas `201`.** O cliente segue o cabeçalho em vez de concatenar
`"/v1/livros/" + id`. Se o formato das URIs mudar, quem usa o `Location` continua funcionando.

**Envelope de erro uniforme.** Todo erro tem a mesma forma, com `tipo` legível por máquina.
O cliente trata erros por uma via só, e um novo tipo de erro não quebra o tratamento existente.

**Versionamento no caminho (`/v1`).** Mudanças incompatíveis podem viver em `/v2` enquanto os
clientes antigos continuam atendidos.

**Paginação com envelope.** Devolver `{"itens": [...], "total": ...}` em vez de um array puro
permitiu acrescentar `total_de_paginas` depois sem quebrar ninguém. Um array no topo do JSON
não tem onde receber metadados: qualquer acréscimo seria mudança incompatível.

**Campos opcionais com padrão.** `pagina`, `tamanho` e os filtros têm valores padrão. Um
cliente que não os conhece funciona sem alteração.

**`ETag` opaco.** O cliente devolve o valor recebido sem interpretá-lo. Hoje é derivado de um
contador; poderia virar um hash do conteúdo sem que nenhum cliente precisasse mudar.

**Erros que não revelam a implementação.** O cliente nunca vê nome de tabela ou coluna, e
portanto não pode depender deles.

### Decisões que aumentam acoplamento

**Ausência de hipermídia.** As respostas não trazem links para as operações relacionadas. O
cliente precisa conhecer previamente o formato de todas as URIs. Um nível mais alto de REST
incluiria links na representação, permitindo ao cliente navegar sem construir caminhos.

**`extra="forbid"` na entrada.** Enviar um campo desconhecido é `422`. Isso é rigor
deliberado — transforma erro de digitação do cliente em falha explícita — mas acopla o cliente
à lista exata de campos aceitos. A alternativa, ignorar campos desconhecidos, aceitaria em
silêncio um `"titlo"` digitado errado e o livro seria criado sem título correto.

**`isbn` obrigatório no `PUT`.** Como o `PUT` substitui a representação inteira, o cliente
precisa conhecer todos os campos. É inerente à semântica do método, e por isso o `PATCH`
existe como alternativa de menor acoplamento.

**Campos derivados na representação.** `exemplares_disponiveis` é conveniente, mas cria
expectativa sobre como o servidor calcula disponibilidade. Mudar a regra — passar a considerar
exemplares em manutenção, por exemplo — mudaria o valor sem mudar o esquema.

### O balanço

O maior acoplamento remanescente é a ausência de hipermídia, e foi uma escolha consciente:
JSON simples é mais direto de demonstrar e de consumir. Em uma API pública, com clientes que
não podem ser atualizados em conjunto, o custo dessa decisão seria maior que o benefício.

---

## 4. Como evitar perda de atualização quando dois clientes editam o mesmo recurso?

### O problema demonstrado

```
Cliente A: GET  /v1/livros/19        → 200, titulo = "A Hora da Estrela"
Cliente B: GET  /v1/livros/19        → 200, titulo = "A Hora da Estrela"
Cliente B: PUT  /v1/livros/19        → 200, titulo = "Título do cliente B"
Cliente A: PUT  /v1/livros/19        → 200, titulo = "Título do cliente A"

Estado final: "Título do cliente A". A alteração de B desapareceu.
```

Ambas as requisições receberam `200`. Nenhum erro foi reportado. B acredita ter gravado, e não
tem como descobrir o contrário sem reler o recurso. Evidência em
`C06 → PUT concorrente SEM If-Match`.

O ponto essencial: **usar HTTP não resolve isso.** O protocolo oferece o mecanismo, mas ele
precisa ser adotado explicitamente.

### A solução implementada: controle de concorrência otimista

Cada livro tem uma coluna `versao`, incrementada a cada alteração real. O `ETag` da resposta é
derivado dela. O cliente devolve esse valor em `If-Match` na escrita, e o servidor compara.

```
Cliente A: GET  /v1/livros/20                  → 200, ETag: "1"
Cliente B: GET  /v1/livros/20                  → 200, ETag: "1"
Cliente B: PUT  /v1/livros/20  If-Match: "1"   → 200, ETag: "2"
Cliente A: PUT  /v1/livros/20  If-Match: "1"   → 412 Precondition Failed

Estado final: "Título do cliente B". Nada foi perdido silenciosamente.
```

Chama-se otimista porque assume que conflitos são raros: em vez de bloquear o recurso durante
a leitura, permite que todos leiam e detecta a colisão apenas no momento da escrita. Se
conflitos fossem frequentes, o custo de refazer o trabalho superaria o de travar.

Ao receber `412`, o cliente relê o recurso, decide o que fazer com a divergência e reenvia com
o `ETag` novo. A decisão volta para quem tem contexto para tomá-la — que é precisamente o
ponto: o servidor não tem como saber se a alteração de A deveria substituir a de B ou ser
mesclada com ela.

Evidência em `C06` e em `testes/test_invariantes.py::test_put_com_if_match_obsoleto_devolve_412`.

### Alternativas e quando usariam

| Estratégia | Como funciona | Quando compensa |
| --- | --- | --- |
| **Otimista com ETag** (implementada) | detecta colisão na escrita | conflitos raros, muitos leitores |
| **Pessimista com bloqueio** | trava o recurso durante a edição | conflitos frequentes, edições longas |
| **Transação com nível de isolamento** | o banco serializa as escritas | tudo em um único banco |
| **Mesclagem automática** | funde alterações em campos distintos | campos independentes entre si |
| **Última escrita vence** | ignora o problema | o dado não é crítico |

O bloqueio pessimista resolve o problema, mas cria outros: um cliente que trava um recurso e
cai deixa-o inacessível até o tempo limite expirar. Em sistema distribuído, isso significa
depender de que todos os participantes se comportem bem — premissa que o otimista não precisa
fazer.

A transação isolada protege contra escritas concorrentes **dentro da mesma requisição**, e é
usada aqui: verificar disponibilidade e inserir o empréstimo acontecem na mesma transação. Mas
ela não protege contra o intervalo entre um `GET` e um `PUT` de clientes diferentes, porque
são duas requisições independentes, possivelmente separadas por minutos. É esse intervalo que
o `ETag` cobre.

### A limitação da implementação atual

O `If-Match` é opcional. Um cliente que não o envie ainda pode sobrescrever alterações alheias,
como o próprio `C06` demonstra. A escolha foi didática: permite exibir o problema e a solução
no mesmo projeto.

Em produção, o caminho seria exigir `If-Match` em toda escrita e responder
`428 Precondition Required` quando ausente, transformando a proteção em obrigação e não em
cortesia do cliente.
