# Documentação da AP4

Serviço remoto de empréstimos de biblioteca com gRPC e Protocol Buffers.

| Documento | Conteúdo |
| --- | --- |
| [01 — Fundamentos de RPC](01-fundamentos-rpc.md) | A ilusão de chamada local, stubs, IDL, marshalling, tipos de RPC, deadlines, status e interceptors. |
| [02 — Contrato e evolução](02-contrato-e-evolucao.md) | O `.proto` campo a campo, as três versões do contrato e o que é mudança compatível. |
| [03 — Roteiro reproduzível](03-roteiro-reproduzivel.md) | Passo a passo para regenerar os stubs, subir o servidor e reproduzir cada experimento. |
| [04 — Evidências](04-evidencias.md) | Tabela de latência/status e de verificações. **Gerado automaticamente.** |
| [05 — Questões de análise](05-questoes-de-analise.md) | As cinco questões da AP4 e a comparação entre gRPC, a AP2 (REST) e a AP3 (MQTT). |
| [06 — Glossário](06-glossario.md) | Termos usados no código e nos documentos. |

## Onde cada requisito da AP4 está atendido

| Requisito obrigatório | Onde | Evidência |
| --- | --- | --- |
| Pelo menos três métodos RPC | [`contratos/emprestimos.proto`](../contratos/emprestimos.proto) | E01 — cinco métodos publicados |
| No mínimo três tipos de mensagem próprios | mesmo arquivo | E01 — onze mensagens |
| Validação explícita e ao menos dois status de erro | [`app/dominio.py`](../app/dominio.py), [`app/erros.py`](../app/erros.py) | E02 — cinco status distintos |
| Cliente com deadline configurado | [`app/cliente.py`](../app/cliente.py) | E03 — 100 ms, 1 s, 3 s |
| Experimento concorrente com múltiplas chamadas | [`experimentos/e05_concorrencia.py`](../experimentos/e05_concorrencia.py) | E05 — 8 clientes, 24 chamadas |
| Mudança compatível no contrato | [`contratos_legado/`](../contratos_legado/) | E07 — cliente antigo contra servidor novo |
