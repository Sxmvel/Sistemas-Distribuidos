# Contrato da API

Base: `http://127.0.0.1:8000` · Prefixo de versão: `/v1` · Documentação interativa: `/docs`

## Visão geral

| # | Método | Caminho | Sucesso | Erros previstos |
| :-: | --- | --- | --- | --- |
| 1 | GET | `/v1/livros` | 200 | 422 |
| 2 | POST | `/v1/livros` | 201 | 409, 422 |
| 3 | GET | `/v1/livros/{id}` | 200, 304 | 404 |
| 4 | PUT | `/v1/livros/{id}` | 200 | 404, 409, 412, 422 |
| 5 | PATCH | `/v1/livros/{id}` | 200 | 404, 409, 412, 422 |
| 6 | DELETE | `/v1/livros/{id}` | 204 | 404, 409, 412 |
| 7 | GET | `/v1/livros/{id}/emprestimos` | 200 | 404 |
| 8 | POST | `/v1/livros/{id}/emprestimos` | 201 | 404, 409, 422 |
| 9 | GET | `/v1/emprestimos/{id}` | 200 | 404 |
| 10 | PATCH | `/v1/emprestimos/{id}` | 200 | 404, 409, 422 |
| 11 | GET | `/v1/saude` | 200 | 503 |
| 12 | GET | `/v1/lento`, `/v1/indisponivel` | 200, 503 | — |

## Livros

### 1. `GET /v1/livros`

Lista paginada, com filtros opcionais.

| Parâmetro | Tipo | Padrão | Restrição |
| --- | --- | --- | --- |
| `pagina` | inteiro | 1 | ≥ 1 |
| `tamanho` | inteiro | 10 | 1 a 100 |
| `autor` | texto | — | busca parcial |
| `titulo` | texto | — | busca parcial |
| `apenas_disponiveis` | booleano | false | — |

```json
{
  "itens": [ ... ],
  "pagina": 1,
  "tamanho": 10,
  "total": 12,
  "total_de_paginas": 2
}
```

O envelope existe para que o cliente saiba quantas páginas há sem precisar percorrer todas.
O teto de 100 itens protege memória e banda: listagem sem limite é o erro comum apontado na
seção de paginação da apostila. Pedir `tamanho=9999` resulta em `422`, não em silenciosa
redução ao máximo — falhar é mais honesto que atender parcialmente sem avisar.

### 2. `POST /v1/livros`

```json
{
  "titulo": "Dom Casmurro",
  "autor": "Machado de Assis",
  "isbn": "9788535910663",
  "ano": 1899,
  "exemplares_total": 3
}
```

Responde `201` com `Location: /v1/livros/{id}` e `ETag: "1"`.

O `Location` evita que o cliente monte a URI por conta própria a partir do id. Isso reduz
acoplamento: se o formato das URIs mudar, clientes que seguem o `Location` continuam
funcionando.

| Campo | Validação |
| --- | --- |
| `titulo` | 2 a 200 caracteres |
| `autor` | 2 a 120 caracteres |
| `isbn` | 10 a 20 caracteres, apenas dígitos, hífen e X, com ao menos 10 dígitos, único |
| `ano` | 1450 a 2100 |
| `exemplares_total` | 1 a 1000 |

Campos não previstos resultam em `422`, por `extra="forbid"`.

### 3. `GET /v1/livros/{id}`

Responde `200` com `ETag` e `Cache-Control: no-cache`.

Enviando `If-None-Match` com o `ETag` atual, responde `304 Not Modified` sem corpo.

O `no-cache` não significa "não guarde em cache". Significa "pode guardar, mas revalide com o
servidor antes de usar". É exatamente o comportamento desejado para um recurso que muda com
frequência moderada: o cliente mantém a cópia e paga apenas uma requisição vazia para
confirmar que ela ainda vale.

### 4. `PUT /v1/livros/{id}`

Substitui a representação inteira. Exige o corpo completo de `LivroEntrada`.

O cabeçalho `If-Match` é **opcional**. Quando enviado, o servidor compara com a versão atual e
responde `412` se não corresponder. Quando ausente, a escrita procede e a última vence.

A escolha de torná-lo opcional é deliberada e didática: permite demonstrar, no mesmo projeto,
tanto a perda de atualização quanto o mecanismo que a impede. Em um sistema de produção com
múltiplos escritores, o caminho seria exigir `If-Match` e responder `428 Precondition Required`
quando ausente.

### 5. `PATCH /v1/livros/{id}`

Atualização parcial. Qualquer subconjunto dos campos de `LivroEntrada`. Corpo vazio resulta
em `422`. Aceita `If-Match` com a mesma semântica do `PUT`.

### 6. `DELETE /v1/livros/{id}`

Responde `204` sem corpo. Responde `409` se houver empréstimo ativo, e `404` se o livro não
existir — inclusive na segunda chamada de um `DELETE` bem-sucedido.

## Empréstimos

### 7. `GET /v1/livros/{id}/emprestimos`

Histórico completo do livro, ativos e devolvidos. Responde `404` se o livro não existir, e não
lista vazia — uma lista vazia afirmaria que o livro existe e não tem empréstimos.

### 8. `POST /v1/livros/{id}/emprestimos`

```json
{ "leitor": "Ana Ribeiro" }
```

Responde `201` com `Location: /v1/emprestimos/{id}`. Responde `409` se não houver exemplar
disponível.

A verificação de disponibilidade e o `INSERT` acontecem na mesma transação, junto com o
incremento da versão do livro. Isso impede que o estado mude entre a checagem e a gravação.

### 9. `GET /v1/emprestimos/{id}`

Empréstimo individual, fora do contexto do livro.

### 10. `PATCH /v1/emprestimos/{id}`

```json
{ "devolvido": true }
```

Registra a devolução preenchendo `devolvido_em`. Responde `409` se já devolvido.

O campo aceita apenas o valor `true`, declarado como `Literal[True]` no esquema. Enviar
`false` resulta em `422`, porque reabrir um empréstimo devolvido não faz parte do contrato.

**Por que não `POST /v1/emprestimos/{id}/devolucao`?** Porque isso colocaria um verbo no
caminho, e a semântica já é expressa pela combinação de recurso e método. A devolução é uma
transição de estado do empréstimo, e alterar parte do estado de um recurso é exatamente o que
`PATCH` significa. A alternativa com verbo seria mais legível à primeira vista, mas cada nova
ação exigiria um novo caminho, e a interface deixaria de ser uniforme.

## Diagnóstico

### 11. `GET /v1/saude`

Responde `200` após consultar o banco de verdade. Responde `503` com `Retry-After` se o banco
estiver inacessível ou se a variável de ambiente `BIBLIOTECA_MANUTENCAO=1` estiver definida.

Uma verificação de saúde que apenas devolve `{"status": "ok"}` fixo não prova nada além de que
o processo está no ar.

### 12. `GET /v1/lento` e `GET /v1/indisponivel`

Endpoints de laboratório para os experimentos da seção 4.8. `/v1/lento?segundos=N` dorme por
N segundos, permitindo observar timeouts do cliente. `/v1/indisponivel` sempre responde `503`
com `Retry-After`, para contrastar com a falha de conexão.

## Cabeçalhos

| Cabeçalho | Direção | Papel |
| --- | --- | --- |
| `Location` | resposta | URI do recurso recém-criado, em `201` |
| `ETag` | resposta | versão da representação |
| `If-None-Match` | requisição | pede `304` se a versão não mudou |
| `If-Match` | requisição | condiciona a escrita à versão informada |
| `Cache-Control` | resposta | política de cache do recurso |
| `Retry-After` | resposta | segundos sugeridos antes de nova tentativa, em `503` |
| `X-Request-ID` | ambos | identificador de correlação, aceito do cliente ou gerado |
| `X-Duracao-Ms` | resposta | tempo de processamento no servidor |
