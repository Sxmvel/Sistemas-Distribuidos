# Índice de estudo — conceito para código

Mapa de cada conceito da apostila até o arquivo onde ele está implementado. É o ponto de
partida para revisar a matéria a partir do código que roda.

## Documentos

| Documento | Conteúdo |
| --- | --- |
| [01 - Fundamentos REST](01-fundamentos-rest.md) | REST como estilo arquitetural, interface uniforme, métodos e status |
| [02 - Modelagem do domínio](02-modelagem-do-dominio.md) | Recursos, relações e as decisões de esquema com suas justificativas |
| [03 - Contrato da API](03-contrato-da-api.md) | Os doze endpoints, com códigos de status e cabeçalhos de cada um |
| [04 - Evidências](04-evidencias.md) | Tabela de testes gerada pela execução dos cenários |
| [05 - Questões de análise](05-questoes-de-analise.md) | As quatro questões da atividade, respondidas |
| [06 - Glossário](06-glossario.md) | Termos usados no projeto |

## Conceitos da apostila

| Seção | Conceito | Onde está implementado |
| --- | --- | --- |
| 4.1 | REST como estilo arquitetural | [`01-fundamentos-rest.md`](01-fundamentos-rest.md) |
| 4.1 | Ausência de sessão no servidor | `app/main.py` — não há estado de conversa entre requisições |
| 4.2 | Recursos e URIs com substantivos | `app/rotas/livros.py`, `app/rotas/emprestimos.py` |
| 4.2 | Método HTTP carrega o verbo | `PATCH /v1/emprestimos/{id}` em vez de `POST /devolucao` |
| 4.2 | Idempotência de PUT e DELETE | `app/repositorios/livros.py` → `substituir`, `remover` |
| 4.3 | Códigos de status | `app/erros.py` → `TITULOS_PADRAO` e as classes de erro |
| 4.4 | Modelos de dados com Pydantic | `app/esquemas.py` |
| 4.5 | Stateless com persistência | `app/db.py` — há banco, não há sessão de aplicação |
| 4.6 | Concorrência e versionamento otimista | `app/concorrencia.py`, coluna `versao` em `app/db.py` |
| 4.6 | Transação para operações compostas | `app/db.py` → `conexao()` |
| 4.7 | Log estruturado e correlação | `app/observabilidade.py` |
| 4.7 | Erro de domínio versus falha interna | `app/erros.py` → `ErroDeDominio` e o tratador genérico |
| 4.8 | Experimentos de timeout e falha | `cliente/cenarios/c07_timeout.py`, `c08_conectividade.py` |
| 4.8 | Idempotência observada na prática | `cliente/cenarios/c05_idempotencia.py` |
| 4.9 | Validação condicional e 304 | `app/rotas/livros.py` → `obter_livro` com `If-None-Match` |
| 4.9 | ETag como identificador de versão | `app/concorrencia.py` → `gerar_etag` |
| 4.10 | Paginação com limite máximo | `app/paginacao.py` |
| 4.10 | Filtros na listagem | `app/repositorios/livros.py` → `montar_filtros` |
| 4.11 | Versionamento da API | prefixo `/v1` em todos os roteadores |
| 4.12 | Validação no limite de confiança | `app/esquemas.py` → `extra="forbid"` e validadores |
| 4.12 | Consultas parametrizadas | `app/repositorios/` — todo valor vai como `?` |
| 4.12 | Erro que não vaza detalhe interno | `app/erros.py` → tradução de `IntegrityError` |
| 4.13 | Testes por invariante e contrato | `testes/test_invariantes.py` |

## Ordem sugerida de leitura do código

```
app/db.py             onde os dados moram e como a transação funciona
app/esquemas.py       o que entra e o que sai, e onde nasce o 422
app/repositorios/     as regras de negócio e o SQL parametrizado
app/erros.py          como uma exceção vira resposta HTTP
app/concorrencia.py   ETag, If-Match e If-None-Match
app/rotas/            a tradução entre HTTP e domínio
app/main.py           a montagem de tudo
cliente/              o consumo da API sob condições adversas
```
