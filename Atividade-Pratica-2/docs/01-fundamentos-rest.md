# Fundamentos REST aplicados a este projeto

## REST não é sinônimo de JSON sobre HTTP

REST é um estilo arquitetural para sistemas hipermídia distribuídos. Em APIs, seus princípios
aparecem em recursos endereçáveis, interface uniforme, mensagens autocontidas e ausência de
sessão de aplicação mantida pelo servidor entre requisições.

JSON é apenas uma das representações possíveis de um recurso. O livro de id 1 é o recurso;
o objeto JSON devolvido pelo `GET /v1/livros/1` é uma representação dele. A distinção fica
visível no `304 Not Modified`: o recurso continua existindo, mas nenhuma representação é
transmitida porque o cliente já possui a versão atual.

## O que o HTTP resolve e que não precisamos reinventar

Na Atividade Prática 1 o protocolo era próprio: o formato ia embutido no payload, separado por
um caractere combinado, e um ACK evitava que duas mensagens chegassem grudadas no buffer TCP.
O HTTP já resolve essas duas coisas:

| Problema | Solução própria (AP1) | Solução do HTTP |
| --- | --- | --- |
| Dizer em que formato os dados estão | prefixo `FORMATO\|payload` | cabeçalho `Content-Type` |
| Saber onde a mensagem termina | ACK a cada envio | cabeçalho `Content-Length` |
| Sinalizar sucesso ou falha | convenção informal | código de status |
| Identificar o alvo da operação | posição na sequência | URI |
| Identificar a intenção | comando embutido no texto | método HTTP |

## Interface uniforme

O mesmo endereço muda de significado conforme o método. Não existe verbo no caminho porque
o verbo já está no método.

```
GET    /v1/livros/1     obter a representação
PUT    /v1/livros/1     substituir a representação
PATCH  /v1/livros/1     alterar parte da representação
DELETE /v1/livros/1     remover o recurso
```

## Seguro e idempotente

| Método | Seguro | Idempotente | Nesta API |
| --- | :-: | :-: | --- |
| GET | sim | sim | nunca altera estado; pode ser repetido à vontade |
| POST | não | não | cada chamada cria um recurso novo com id novo |
| PUT | não | sim | substitui a representação inteira pelo corpo enviado |
| PATCH | não | sim (aqui) | aplica campos absolutos, sem operações relativas |
| DELETE | não | sim quanto ao efeito | o recurso fica ausente; o status muda de 204 para 404 |

**Seguro** significa que a operação não modifica estado. **Idempotente** significa que repetir
a requisição leva ao mesmo estado final que executá-la uma vez.

Duas escolhas de projeto tornam a idempotência observável, e não apenas teórica:

1. **`PUT` só incrementa a versão quando algum campo muda de fato.** Sem isso, repetir um `PUT`
   idêntico alteraria o `ETag` e o corpo devolvido, quebrando a idempotência que se pretende
   demonstrar. Ver `app/repositorios/livros.py`.
2. **`PATCH` aceita apenas valores absolutos.** Se aceitasse algo como "acrescente 1 ao total de
   exemplares", cada repetição produziria um resultado diferente e o método deixaria de ser
   idempotente. O `PATCH` desta API é idempotente porque seu contrato foi desenhado assim.

## Stateless

Cada requisição carrega tudo o que é necessário para ser interpretada. Não há sessão no
servidor, nem estado de conversa entre chamadas.

Isso não proíbe banco de dados. O estado do domínio é persistente e compartilhado; o que não
existe é estado de conversação invisível associado a um cliente específico. Duas consequências
práticas: qualquer instância da API pode atender qualquer requisição, e uma instância pode ser
reiniciada sem que os clientes percam contexto.

## Códigos de status usados nesta API

| Código | Quando | Exemplo |
| --- | --- | --- |
| 200 | operação concluída com corpo | `GET /v1/livros/1` |
| 201 | recurso criado, com `Location` | `POST /v1/livros` |
| 204 | sucesso sem corpo | `DELETE /v1/livros/1` |
| 304 | representação não mudou | `GET` com `If-None-Match` atual |
| 404 | recurso inexistente | `GET /v1/livros/999999` |
| 409 | conflito com o estado atual | emprestar livro sem exemplar livre |
| 412 | precondição falhou | `PUT` com `If-Match` obsoleto |
| 422 | entrada semanticamente inválida | `ano=99` |
| 500 | falha inesperada | erro não previsto, sem detalhe interno no corpo |
| 503 | indisponibilidade temporária | `GET /v1/indisponivel`, com `Retry-After` |

### A diferença entre 400 e 422

`400 Bad Request` é para entrada inválida em nível geral, quando a requisição sequer pode ser
interpretada. `422 Unprocessable Content` é para uma representação sintaticamente válida que
falha em uma regra semântica. Um JSON com `"ano": 99` é JSON perfeitamente formado, e o campo
existe e é do tipo certo — o que falha é a regra de domínio. Por isso 422.

### A diferença entre 404 e 409

`404` responde "esse recurso não existe". `409` responde "o recurso existe, sua requisição é
válida, mas ela colide com o estado atual dele". Tentar emprestar um livro sem exemplar livre
não é erro de entrada nem recurso ausente: é conflito de estado.

### A diferença entre 409 e 412

Ambos indicam conflito, mas de naturezas distintas. O `409` vem de uma regra do domínio
(não há exemplar disponível). O `412` vem de uma precondição explícita que o cliente enviou
e que o servidor verificou (`If-Match`). O 412 só existe porque o cliente pediu para ser
protegido contra escrita concorrente.

## Formato dos erros

Todos os erros usam o mesmo envelope, servido como `application/problem+json`:

```json
{
  "tipo": "conflito-de-estado",
  "titulo": "Conflito com o estado atual",
  "status": 409,
  "detalhe": "Não há exemplares disponíveis do livro 3: 1 de 1 estão emprestados.",
  "instancia": "/v1/livros/3/emprestimos",
  "correlacao": "8246d4ecb173"
}
```

O campo `correlacao` é o mesmo identificador que aparece na linha de log daquela requisição.
Um usuário que relata um erro informando esse código permite localizar a requisição exata no
log, sem busca por horário aproximado.
