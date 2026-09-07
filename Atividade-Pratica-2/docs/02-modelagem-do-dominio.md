# Modelagem do domínio

O domínio é o acervo de uma biblioteca, escolhido por ser diferente do exemplo de
dispositivos e leituras da apostila e por produzir conflitos de estado naturais e fáceis de
demonstrar.

## Recursos e relação

```
   Livro  1 ─────────────< N  Emprestimo
```

Um livro possui vários empréstimos ao longo do tempo. Um empréstimo pertence a exatamente um
livro. A relação aparece na URI: `/v1/livros/{id}/emprestimos`.

O empréstimo também é endereçável fora do pai, em `/v1/emprestimos/{id}`, porque depois de
criado ele tem identidade própria e é manipulado de forma independente. A URI aninhada serve
para criar e listar no contexto do livro; a URI de topo serve para operar sobre um empréstimo
específico.

## Esquema

```sql
CREATE TABLE livros (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT    NOT NULL,
    autor            TEXT    NOT NULL,
    isbn             TEXT    NOT NULL UNIQUE,
    ano              INTEGER NOT NULL,
    exemplares_total INTEGER NOT NULL,
    versao           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE emprestimos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    livro_id      INTEGER NOT NULL REFERENCES livros(id) ON DELETE CASCADE,
    leitor        TEXT    NOT NULL,
    emprestado_em TEXT    NOT NULL,
    devolvido_em  TEXT
);
```

## As decisões que não são óbvias

### 1. A coluna `versao` não pertence ao domínio

Nenhum bibliotecário quer saber a versão de um livro. Ela existe para o controle de
concorrência otimista: é a partir dela que o `ETag` é gerado.

```
Cliente A: GET /v1/livros/1    → 200, ETag: "3"
Cliente B: GET /v1/livros/1    → 200, ETag: "3"
Cliente B: PUT If-Match: "3"   → 200, ETag: "4"
Cliente A: PUT If-Match: "3"   → 412 Precondition Failed
```

Sem ela, a escrita de A sobrescreveria a de B em silêncio.

A versão é incrementada também quando um empréstimo é criado ou devolvido, porque isso muda
`exemplares_disponiveis` — e o `ETag` identifica a **representação**, não a linha da tabela.
Se a representação muda, o `ETag` precisa mudar junto, sob pena de um cliente com cache
receber `304` para um conteúdo que na verdade é diferente.

### 2. `isbn` é `UNIQUE`, e é daí que nasce o 409

O banco lança `sqlite3.IntegrityError` ao receber um isbn repetido. O repositório captura essa
exceção e a traduz em `ConflitoDeEstado`, que vira `409`. A mensagem original —
`UNIQUE constraint failed: livros.isbn` — nunca chega ao cliente, porque revelaria nomes de
tabela e coluna.

```
sqlite3.IntegrityError  →  ConflitoDeEstado  →  409 Conflict
   (erro técnico)          (erro de negócio)     (resposta HTTP)
```

### 3. Não existe coluna `exemplares_disponiveis`

O número de exemplares disponíveis é derivado, calculado em toda consulta:

```sql
exemplares_total - (
    SELECT COUNT(*) FROM emprestimos e
    WHERE e.livro_id = l.id AND e.devolvido_em IS NULL
)
```

Guardar o valor numa coluna exigiria mantê-lo sincronizado a cada empréstimo e devolução, e
qualquer falha nessa sincronização faria o banco mentir. Calculando, é impossível divergir.
O custo é uma subconsulta; o benefício é que o dado nunca está errado.

A regra geral: **não guarde o que pode ser deduzido**. Todo dado duplicado é um dado que pode
divergir.

### 4. `devolvido_em` aceita nulo, e não existe coluna `status`

| `devolvido_em` | Significado |
| --- | --- |
| `NULL` | empréstimo ativo |
| `2026-09-03T20:26:29+00:00` | devolvido, com a data |

Um campo carrega duas informações e elimina a possibilidade de um `status = "devolvido"`
conviver com `devolvido_em = NULL`. É o mesmo princípio da decisão anterior.

Datas são `TEXT` porque o SQLite não possui tipo de data. São sempre gravadas em ISO 8601 UTC.
Em sistema distribuído, gravar horário local faz cada máquina contar uma história diferente.

### 5. A regra de remoção mora no código, não na constraint

`ON DELETE CASCADE` faz o banco apagar os empréstimos junto com o livro. Mas a regra
*"não se apaga livro com empréstimo ativo"* está no repositório, como verificação explícita
que produz `409`.

O motivo é de legibilidade: uma regra de negócio precisa estar visível onde a operação é lida.
A constraint do banco é a última linha de defesa contra corrupção, não o lugar onde as
decisões de domínio são declaradas.

### 6. `PUT` não cria recurso em id escolhido pelo cliente

`PUT /v1/livros/999999` devolve `404` em vez de criar. O identificador é gerado pelo servidor,
e permitir que o cliente escolha abriria buracos na sequência e transferiria para ele uma
responsabilidade que não é sua. Criar é sempre `POST` na coleção.

## Modelos de entrada e de saída são separados

`app/esquemas.py` define classes distintas para o que entra e o que sai:

| Classe | Papel |
| --- | --- |
| `LivroEntrada` | o que o cliente pode enviar em `POST` e `PUT` |
| `LivroParcial` | o que o cliente pode enviar em `PATCH`, todos os campos opcionais |
| `Livro` | o que a API devolve, incluindo `id`, `versao` e `exemplares_disponiveis` |

A separação não é burocracia. Se houvesse um único modelo, o cliente poderia enviar `id`,
`versao` ou `exemplares_disponiveis` no corpo — campos que só o servidor tem autoridade para
definir. Com modelos separados e `extra="forbid"`, tentar enviá-los resulta em `422`.
