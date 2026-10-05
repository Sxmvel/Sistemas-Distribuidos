# Roteiro reproduzível

Todos os comandos partem da pasta `Atividade-Pratica-5` e usam o interpretador do ambiente
virtual pelo caminho explícito, que funciona mesmo sem ativar o `.venv`.

## 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest
```

81 testes, cerca de 4 s. Usam o `TestClient` do FastAPI com banco temporário e não dependem de
servidor no ar.

## 3. Experimentos

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos
```

Cerca de 75 s. Ao final:

- `docs/04-evidencias.md` — tabela de classificação, métricas, tentativas e verificações;
- `logs/tentativas.csv` — cada tentativa medida no cliente;
- `logs/<cenario>-<servidor>.jsonl` — cada requisição recebida por cada servidor;
- `logs/<cenario>-<servidor>.saida.txt` — saída de console do uvicorn.

Para rodar só alguns cenários:

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos E05 E06
```

## 4. Variáveis de ambiente do servidor

| Variável | Padrão | Uso |
| --- | --- | --- |
| `BIBLIOTECA_LABORATORIO` | `0` | `1` liga `/experimento/instavel` |
| `BIBLIOTECA_ATRASO_NA_ESCRITA` | `0` | segundos de espera depois de gravar um empréstimo |
| `BIBLIOTECA_SEMENTE` | aleatória | semente do sorteio de `prob_falha` |
| `BIBLIOTECA_BANCO` | `biblioteca.db` | arquivo SQLite |
| `BIBLIOTECA_LOG` | `logs/api.jsonl` | log estruturado |
| `BIBLIOTECA_PROCESSO` | `api` | identificador gravado em cada linha do log |
| `BIBLIOTECA_TOKEN_BIBLIOTECARIO` | `lab-bibliotecario-troque-me` | token do papel bibliotecario |
| `BIBLIOTECA_TOKEN_ATENDENTE` | `lab-atendente-troque-me` | token do papel atendente |
| `BIBLIOTECA_TOKEN_CONSULTA` | `lab-consulta-troque-me` | token do papel consulta |

Os experimentos sempre geram tokens novos; os valores padrão existem só para o uso manual em
desenvolvimento e o E10 confirma que eles não são aceitos durante os experimentos.

## 5. Uso manual da API

Terminal 1:

```powershell
$env:BIBLIOTECA_LABORATORIO = "1"
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Terminal 2:

```powershell
curl.exe -i "http://127.0.0.1:8000/experimento/instavel?atraso_ms=300&prob_falha=0.5"
curl.exe -i -X POST http://127.0.0.1:8000/v1/livros/1/emprestimos -H "Content-Type: application/json" -d "{\"leitor\": \"Ana\"}"
curl.exe -i -X POST http://127.0.0.1:8000/v1/livros/1/emprestimos -H "Authorization: Bearer lab-consulta-troque-me" -H "Content-Type: application/json" -d "{\"leitor\": \"Ana\"}"
curl.exe -i -X POST http://127.0.0.1:8000/v1/livros/1/emprestimos -H "Authorization: Bearer lab-atendente-troque-me" -H "Idempotency-Key: demo-0001" -H "Content-Type: application/json" -d "{\"leitor\": \"Ana\"}"
```

Respostas esperadas: 200 ou 503; 401; 403; 201 (repetir o último comando devolve 201 com
`Idempotent-Replayed: true` e o mesmo id). A documentação interativa fica em
`http://127.0.0.1:8000/docs`.

## 6. Demonstração

O cenário sugerido para apresentar é o **E06**, porque mostra em menos de 10 s a diferença entre
o que o cliente vê e o que o sistema fez:

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_todos E06
```

Roteiro de fala:

1. **Hipótese.** O servidor grava o empréstimo e só responde 800 ms depois. O cliente desiste em
   500 ms e tenta de novo.
2. **Observação no cliente.** Três tentativas, três timeouts. Para o cliente, nada aconteceu.
3. **Observação no servidor.** `logs/e06-servidor.jsonl` tem a mesma correlação três vezes, com
   `tentativa` 1, 2 e 3, todas com status 201.
4. **Efeito.** Ana ficou com três empréstimos e Bruno, um leitor que não participou de nada,
   recebeu 409 porque os exemplares acabaram.
5. **Correção.** Com `Idempotency-Key`, as mesmas três tentativas e os mesmos três timeouts
   deixam um único empréstimo, e a repetição com prazo maior devolve o mesmo id marcado como
   `Idempotent-Replayed`.
6. **Classificação.** Falha de temporização no cliente que, com retry cego numa operação não
   idempotente, vira falha de resposta do sistema (transição de estado incorreta).

Uma alternativa interativa, com o servidor da seção 5 no ar:

```powershell
.\.venv\Scripts\python.exe -m cliente.demonstracao --prob-falha 0.5 --chamadas 5
```
