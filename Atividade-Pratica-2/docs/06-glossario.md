# Glossário

**Cache-Control** — cabeçalho que define a política de cache. `no-cache` não proíbe o
armazenamento: obriga a revalidar com o servidor antes de usar a cópia guardada.

**ConnectionError** — falha de transporte, antes de qualquer mensagem HTTP existir. Não possui
código de status porque nenhuma resposta chegou a ser produzida.

**Content negotiation** — mecanismo pelo qual o cliente informa, via `Accept`, em qual formato
deseja a representação. Esta API oferece apenas JSON.

**Controle de concorrência otimista** — permite que todos leiam livremente e detecta a colisão
apenas no momento da escrita. O oposto é o pessimista, que bloqueia o recurso durante a edição.

**Correlação (X-Request-ID)** — identificador que acompanha uma operação por todos os serviços
que ela atravessa. Aceito do cliente quando enviado, gerado quando ausente, e presente tanto
na resposta quanto na linha de log.

**ETag** — identificador de uma versão específica da representação de um recurso. Valor opaco
para o cliente, que deve devolvê-lo sem interpretar. Aqui é derivado da coluna `versao`.

**Idempotente** — repetir a operação leva ao mesmo estado final que executá-la uma vez.
Propriedade do efeito sobre o estado, não da resposta devolvida.

**If-Match** — cabeçalho de requisição que condiciona a escrita a que o recurso ainda esteja na
versão informada. Falha com `412`.

**If-None-Match** — cabeçalho de requisição que pede a representação apenas se ela mudou.
Quando não mudou, responde `304` sem corpo.

**Interface uniforme** — o mesmo conjunto pequeno de métodos se aplica a todos os recursos.
O verbo fica no método HTTP, não no caminho da URI.

**Location** — cabeçalho devolvido em `201` com a URI do recurso recém-criado, para que o
cliente não precise montá-la.

**Lost update** — perda de atualização. Dois clientes leem a mesma versão, ambos gravam, e a
alteração do primeiro desaparece sem que ninguém seja notificado.

**Paginação** — divisão de uma listagem em páginas. Esta API usa página e tamanho, com teto de
100 itens. Cursores são preferíveis em conjuntos muito mutáveis, por reduzirem inconsistências
causadas por inserções entre páginas.

**problem+json** — tipo de mídia para corpos de erro estruturados, definido pela RFC 9457.
Padroniza o formato de erro para que o cliente trate todos por uma via só.

**Recurso** — a entidade conceitual identificada por uma URI. O livro de id 1 é o recurso; o
JSON devolvido é uma de suas representações possíveis.

**Representação** — a forma serializada de um recurso em um dado momento. O `304` deixa a
distinção visível: o recurso continua existindo, mas nenhuma representação é transmitida.

**Retry-After** — cabeçalho que acompanha o `503` sugerindo quantos segundos esperar antes de
tentar novamente.

**Safe (seguro)** — a operação não modifica o estado do recurso. `GET` é seguro; `POST`,
`PUT`, `PATCH` e `DELETE` não são.

**Stateless** — cada requisição carrega tudo que é necessário para ser interpretada. Não
proíbe banco de dados: o que não existe é estado de conversação mantido no servidor entre
requisições de um mesmo cliente.

**Sub-recurso** — recurso que existe no contexto de outro, expresso pelo aninhamento na URI:
`/v1/livros/{id}/emprestimos`.

**Teste de contrato** — verifica que cliente e servidor concordam sobre esquema e semântica.

**Teste por invariante** — verifica propriedades que devem valer sempre, independentemente dos
dados. Exemplo: depois de `DELETE`, `GET` nunca devolve representação.

**Transação** — conjunto de operações que ocorre por inteiro ou não ocorre. Implementada em
`app/db.py`, onde o `commit` acontece apenas se o bloco `with` terminar sem exceção.

**URI** — identificador do recurso. Modelada com substantivos e relações estáveis.

**Versionamento otimista** — ver controle de concorrência otimista.
