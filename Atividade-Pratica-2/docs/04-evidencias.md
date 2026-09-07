# Evidências de teste

> Documento gerado automaticamente por `cliente/executar_todos.py`.
> Execução em 03/09/2026 17:53:31 contra `http://127.0.0.1:8000` com timeout de 3.0s no cliente.

**Resultado: 44 de 44 verificações conforme o esperado.**

---

## C01 - Fluxo feliz

Percurso completo de criação, leitura, empréstimo e devolução.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `POST /v1/livros` | 201 | 201 | ✅ | Criação devolve 201 e o cabeçalho Location aponta para o recurso novo, evitando que o cliente monte URIs na mão: /v1/livros/13 |
| `GET /v1/livros/13` | 200 | 200 | ✅ | A representação traz exemplares_disponiveis=2, campo derivado em consulta e não armazenado, portanto sempre coerente com os empréstimos. |
| `POST /v1/livros/13/emprestimos` | 201 | 201 | ✅ | Sub-recurso criado sob o livro: a URI expressa a relação 1-para-N sem precisar de verbo no caminho. |
| `GET /v1/livros/13/emprestimos` | 200 | 200 | ✅ | A coleção filtrada pelo pai retorna 1 item(ns), sem exigir filtro do cliente. |
| `PATCH /v1/emprestimos/5` | 200 | 200 | ✅ | A devolução é uma transição de estado do empréstimo, modelada como PATCH no recurso e não como POST /devolucao: o verbo fica no método HTTP, não na URI. |
| `GET /v1/livros/13 (após devolução)` | 200 | 200 | ✅ | exemplares_disponiveis voltou a 2 automaticamente, porque o número é calculado e não mantido em coluna própria. |


## C02 - Validação de entrada

Representações sintaticamente válidas mas semanticamente inválidas resultam em 422.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `POST /v1/livros com ano=99` | 422 | 422 | ✅ | O JSON é sintaticamente válido, então não é 400: o corpo foi entendido e reprovado na regra de domínio (ano entre 1450 e 2100). Esse é exatamente o caso do 422. |
| `POST /v1/livros com titulo de 1 caractere` | 422 | 422 | ✅ | Restrição de tamanho mínimo declarada no esquema Pydantic, validada antes de qualquer acesso ao banco: a entrada inválida nunca chega a persistir estado. |
| `POST /v1/livros com isbn fora do formato` | 422 | 422 | ✅ | Validador de campo próprio: o isbn aceita apenas dígitos, hífen e X, com no mínimo 10 dígitos. Validar no limite de confiança é o princípio da seção de segurança. |
| `POST /v1/livros com campo desconhecido` | 422 | 422 | ✅ | extra=forbid rejeita campos não previstos em vez de ignorá-los em silêncio, o que transforma erro de digitação do cliente em falha explícita. |
| `GET /v1/livros?tamanho=9999` | 422 | 422 | ✅ | O limite máximo de 100 itens por página protege memória e banda do servidor: listagem sem teto é o erro comum que a apostila aponta na seção de paginação. |
| `PATCH /v1/livros/1 com corpo vazio` | 422 | 422 | ✅ | PATCH sem nenhum campo não tem significado: é rejeitado por um validador de modelo, não por uma checagem espalhada na rota. |
| `Formato do corpo de erro (application/problem+json)` | campos presentes | campos presentes | ✅ | Todos os erros usam o mesmo envelope, com o identificador de correlação que também está no log: o cliente relata o id e o servidor acha a requisição exata. |


## C03 - Recurso inexistente

Toda referência a um recurso que não existe resulta em 404, inclusive em sub-recursos.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `GET /v1/livros/999999` | 404 | 404 | ✅ | A URI é sintaticamente válida e o recurso simplesmente não existe. O detalhe é específico e não vaza estrutura interna: Não existe livro com id 999999. |
| `GET /v1/emprestimos/999999` | 404 | 404 | ✅ | Empréstimo também é recurso de primeira classe, endereçável fora do livro pai. |
| `GET /v1/livros/999999/emprestimos` | 404 | 404 | ✅ | Listar sub-recurso de pai inexistente é 404, não 200 com lista vazia: lista vazia afirmaria que o livro existe e não tem empréstimos. |
| `POST /v1/livros/999999/emprestimos` | 404 | 404 | ✅ | O corpo é válido, então não é 422: o que falha é a existência do pai referenciado na URI. |
| `PUT /v1/livros/999999` | 404 | 404 | ✅ | Decisão de projeto: PUT não cria recurso em id escolhido pelo cliente, porque o id é gerado pelo servidor. Permitir criação por PUT abriria buracos na sequência de ids. |
| `GET /v1/rota-que-nao-existe` | 404 | 404 | ✅ | Até o 404 de rota desconhecida usa o mesmo envelope de erro, mantendo o contrato uniforme para o cliente. |


## C04 - Conflito com o estado atual

Requisições válidas que colidem com o estado do recurso resultam em 409.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `POST /v1/livros com isbn já cadastrado` | 409 | 409 | ✅ | O isbn é UNIQUE no banco. O IntegrityError do SQLite é capturado no repositório e traduzido em erro de domínio: a mensagem técnica com nome de tabela nunca chega ao cliente. |
| `POST /v1/livros/15/emprestimos sem exemplar livre` | 409 | 409 | ✅ | Regra de negócio verificada dentro da mesma transação que faria o INSERT, e não em uma consulta anterior solta: entre a checagem e a gravação nada muda. |
| `DELETE /v1/livros/15 com empréstimo ativo` | 409 | 409 | ✅ | A regra vive no código do repositório, não numa constraint do banco: regra de negócio precisa estar visível onde se lê a operação. |
| `PATCH /v1/emprestimos/6 já devolvido` | 409 | 409 | ✅ | Transição de estado inválida: devolver duas vezes não é erro de entrada, é conflito com o estado atual do recurso. Por isso 409 e não 422. |
| `DELETE /v1/livros/15 após devolução` | 204 | 204 | ✅ | Devolvido o exemplar, o conflito desaparece e a mesma requisição que falhava passa: o 409 depende do estado, não da requisição. |


## C05 - Idempotência

Comparação entre POST, PUT e DELETE quanto ao efeito de repetir a mesma requisição.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `POST /v1/livros repetido (isbn diferente)` | ids distintos | ids distintos | ✅ | POST não é idempotente por definição: cada chamada cria um recurso novo, com URI nova. É por isso que o servidor, e não o cliente, escolhe o identificador. |
| `PUT /v1/livros/18 idêntico duas vezes` | 200 | 200 | ✅ | Ambas retornam 200 e o mesmo corpo: PUT substitui a representação inteira, então repetir leva ao mesmo estado final. |
| `ETag após o PUT repetido ("2" vs "2")` | ETag idêntico | ETag idêntico | ✅ | O repositório só incrementa a versão quando algum campo realmente muda. Sem isso, repetir um PUT idêntico alteraria o ETag e quebraria a idempotência observável. |
| `DELETE /v1/livros/18 (primeira vez)` | 204 | 204 | ✅ | 204 sem corpo: não há representação a devolver depois de remover o recurso. |
| `DELETE /v1/livros/18 (segunda vez)` | 404 | 404 | ✅ | O efeito é idempotente (o recurso continua ausente), mas o status difere. Idempotência é uma propriedade do estado resultante, não da resposta. |
| `GET /v1/livros/18 após DELETE` | 404 | 404 | ✅ | Invariante de contrato: depois de DELETE bem-sucedido, GET no mesmo URI nunca pode devolver representação. |


## C06 - Concorrência e cache condicional

Perda de atualização entre dois clientes, e como ETag com If-Match a impede.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `GET /v1/livros/19 devolve ETag` | ETag presente | ETag presente | ✅ | O cabeçalho veio como ETag: "1". Ele identifica a versão da representação e é derivado da coluna versao, incrementada a cada alteração real do recurso. |
| `GET /v1/livros/19 com If-None-Match` | 304 | 304 | ✅ | Resposta sem corpo (0 bytes): o cliente já tem a versão atual. Economiza banda e deixa explícito que representação e recurso são coisas diferentes. |
| `PUT concorrente SEM If-Match (dois clientes)` | última escrita vence | última escrita vence | ✅ | Perda de atualização demonstrada: A e B leram a mesma versão, ambos gravaram com 200 e a alteração de B sumiu sem aviso. Estado final: 'Título escrito pelo cliente A'. |
| `PUT /v1/livros/20 do cliente B com If-Match válido` | 200 | 200 | ✅ | B chegou primeiro com a versão correta e gravou. O ETag avançou para "2". |
| `PUT /v1/livros/20 do cliente A com If-Match obsoleto` | 412 | 412 | ✅ | A escrita de A é recusada porque a precondição falhou. Nada foi sobrescrito: o mesmo cenário que perdeu dados sem If-Match agora falha alto e visivelmente. |
| `GET /v1/livros/20 após o conflito` | escrita de B preservada | escrita de B preservada | ✅ | Controle de concorrência otimista: em vez de travar o recurso, o servidor detecta a colisão na hora da escrita e devolve a decisão ao cliente. |


## C07 - Timeout

A mesma rota lenta observada sob três limites de tempo diferentes no cliente.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `GET /v1/lento?segundos=2.0 com timeout=0.5s` | Timeout | Timeout | ✅ | O servidor processou normalmente; quem desistiu foi o cliente. A operação pode ter sido concluída do outro lado, e o cliente não tem como saber. |
| `GET /v1/lento?segundos=2.0 com timeout=1.0s` | Timeout | Timeout | ✅ | O servidor processou normalmente; quem desistiu foi o cliente. A operação pode ter sido concluída do outro lado, e o cliente não tem como saber. |
| `GET /v1/lento?segundos=2.0 com timeout=3.0s` | 200 | 200 | ✅ | Dentro do limite, a resposta chega íntegra: o timeout é uma decisão do cliente sobre quanto tempo aceita esperar, não uma propriedade do servidor. |
| `Timeout definido em todas as chamadas do cliente` | sim | sim | ✅ | cliente/comum.py define TIMEOUT=3.0 e o repassa em toda requisição. Sem timeout, a biblioteca requests espera indefinidamente e um serviço lento derruba o chamador. |


## C08 - Falha de conectividade

Diferença entre o servidor responder erro e o cliente não conseguir resposta alguma.

| Requisição | Esperado | Obtido | OK | Análise |
| --- | --- | --- | :-: | --- |
| `GET http://127.0.0.1:65000/v1/livros (sem servidor)` | ConnectionError | ConnectionError | ✅ | Não existe status HTTP aqui: a falha é de transporte, antes de qualquer mensagem HTTP. O cliente não sabe se o serviço caiu, se a rede falhou ou se a porta está errada. |
| `GET /v1/indisponivel` | 503 | 503 | ✅ | Aqui existe resposta HTTP: o servidor está no ar e declara indisponibilidade temporária, com Retry-After=5s orientando quando tentar de novo. |
| `GET /v1/saude` | 200 | 200 | ✅ | A verificação de saúde consulta o banco de verdade antes de responder 200: um health check que só devolve 'ok' fixo não prova nada. |
| `Comparação: ConnectionError versus 503` | distinguíveis | distinguíveis | ✅ | 503 é informação do servidor e permite repetição orientada. ConnectionError é ausência de informação: repetir uma escrita nesse caso arrisca duplicar efeito já aplicado. |

