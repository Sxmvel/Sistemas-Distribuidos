#!/usr/bin/env bash
set -u

BASE="http://127.0.0.1:8000"
ISBN="978$(date +%s)0"

titulo() {
    printf '\n\033[1m%s\033[0m\n' "$1"
}

titulo "1. Saude do servico"
curl -i -s "$BASE/v1/saude"

titulo "2. Listagem paginada"
curl -i -s "$BASE/v1/livros?pagina=1&tamanho=3"

titulo "3. Tamanho de pagina acima do limite (422)"
curl -i -s "$BASE/v1/livros?tamanho=9999"

titulo "4. Cadastro de livro (201 com Location e ETag)"
curl -i -s -X POST "$BASE/v1/livros" \
    -H "Content-Type: application/json" \
    -d "{\"titulo\":\"O Cortico\",\"autor\":\"Aluisio Azevedo\",\"isbn\":\"$ISBN\",\"ano\":1890,\"exemplares_total\":2}"

LIVRO=$(curl -s "$BASE/v1/livros?titulo=O%20Cortico&tamanho=1" | python -c "import sys,json; print(json.load(sys.stdin)['itens'][0]['id'])")
ETAG=$(curl -s -i "$BASE/v1/livros/$LIVRO" | grep -i '^etag:' | tr -d '\r' | cut -d' ' -f2)

titulo "5. Cadastro com isbn repetido (409)"
curl -i -s -X POST "$BASE/v1/livros" \
    -H "Content-Type: application/json" \
    -d "{\"titulo\":\"Outro\",\"autor\":\"Outro\",\"isbn\":\"$ISBN\",\"ano\":2000,\"exemplares_total\":1}"

titulo "6. Cadastro com ano invalido (422)"
curl -i -s -X POST "$BASE/v1/livros" \
    -H "Content-Type: application/json" \
    -d '{"titulo":"Invalido","autor":"Autor","isbn":"9780000000001","ano":99,"exemplares_total":1}'

titulo "7. Obter livro $LIVRO (200 com ETag $ETAG)"
curl -i -s "$BASE/v1/livros/$LIVRO"

titulo "8. Livro inexistente (404)"
curl -i -s "$BASE/v1/livros/999999"

titulo "9. Validacao condicional com If-None-Match (304)"
curl -i -s "$BASE/v1/livros/$LIVRO" -H "If-None-Match: $ETAG"

titulo "10. PUT com If-Match correto (200)"
curl -i -s -X PUT "$BASE/v1/livros/$LIVRO" \
    -H "Content-Type: application/json" \
    -H "If-Match: $ETAG" \
    -d "{\"titulo\":\"O Cortico (revisado)\",\"autor\":\"Aluisio Azevedo\",\"isbn\":\"$ISBN\",\"ano\":1890,\"exemplares_total\":2}"

titulo "11. PUT com If-Match obsoleto (412)"
curl -i -s -X PUT "$BASE/v1/livros/$LIVRO" \
    -H "Content-Type: application/json" \
    -H "If-Match: $ETAG" \
    -d "{\"titulo\":\"Sobrescrita perdida\",\"autor\":\"Aluisio Azevedo\",\"isbn\":\"$ISBN\",\"ano\":1890,\"exemplares_total\":2}"

titulo "12. Registrar emprestimo (201)"
curl -i -s -X POST "$BASE/v1/livros/$LIVRO/emprestimos" \
    -H "Content-Type: application/json" \
    -d '{"leitor":"Ana Ribeiro"}'

titulo "13. Segundo emprestimo (201, ultimo exemplar)"
curl -i -s -X POST "$BASE/v1/livros/$LIVRO/emprestimos" \
    -H "Content-Type: application/json" \
    -d '{"leitor":"Bruno Tavares"}'

titulo "14. Terceiro emprestimo sem exemplar livre (409)"
curl -i -s -X POST "$BASE/v1/livros/$LIVRO/emprestimos" \
    -H "Content-Type: application/json" \
    -d '{"leitor":"Carla Nunes"}'

titulo "15. Listar emprestimos do livro"
curl -i -s "$BASE/v1/livros/$LIVRO/emprestimos"

titulo "16. DELETE com emprestimo ativo (409)"
curl -i -s -X DELETE "$BASE/v1/livros/$LIVRO"

titulo "17. Rota que sempre responde 503"
curl -i -s "$BASE/v1/indisponivel"

titulo "18. Timeout do cliente menor que a rota lenta"
curl -i -s --max-time 1 "$BASE/v1/lento?segundos=2" || echo "curl abortou por timeout: nao houve resposta HTTP"

titulo "19. Sem servidor na porta 65000 (falha de conexao)"
curl -i -s "http://127.0.0.1:65000/v1/livros" || echo "curl nao conseguiu conectar: nao existe status HTTP"
