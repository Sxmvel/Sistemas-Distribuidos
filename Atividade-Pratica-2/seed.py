from app import db
from app.repositorios import emprestimos, livros

ACERVO = [
    {"titulo": "Dom Casmurro", "autor": "Machado de Assis", "isbn": "9788535910663", "ano": 1899, "exemplares_total": 3},
    {"titulo": "Grande Sertão: Veredas", "autor": "João Guimarães Rosa", "isbn": "9788520925157", "ano": 1956, "exemplares_total": 2},
    {"titulo": "Vidas Secas", "autor": "Graciliano Ramos", "isbn": "9788503012301", "ano": 1938, "exemplares_total": 1},
    {"titulo": "Memórias Póstumas de Brás Cubas", "autor": "Machado de Assis", "isbn": "9788572329972", "ano": 1881, "exemplares_total": 4},
    {"titulo": "A Hora da Estrela", "autor": "Clarice Lispector", "isbn": "9788520937006", "ano": 1977, "exemplares_total": 2},
    {"titulo": "O Cortiço", "autor": "Aluísio Azevedo", "isbn": "9788572322270", "ano": 1890, "exemplares_total": 3},
    {"titulo": "Capitães da Areia", "autor": "Jorge Amado", "isbn": "9788535914092", "ano": 1937, "exemplares_total": 2},
    {"titulo": "Iracema", "autor": "José de Alencar", "isbn": "9788508133055", "ano": 1865, "exemplares_total": 1},
    {"titulo": "Macunaíma", "autor": "Mário de Andrade", "isbn": "9788526017351", "ano": 1928, "exemplares_total": 2},
    {"titulo": "O Alienista", "autor": "Machado de Assis", "isbn": "9788594318602", "ano": 1882, "exemplares_total": 5},
    {"titulo": "Sagarana", "autor": "João Guimarães Rosa", "isbn": "9788520939246", "ano": 1946, "exemplares_total": 2},
    {"titulo": "Laços de Família", "autor": "Clarice Lispector", "isbn": "9788532508126", "ano": 1960, "exemplares_total": 1},
]

EMPRESTIMOS_INICIAIS = [
    (3, "Ana Ribeiro"),
    (8, "Bruno Tavares"),
    (1, "Carla Nunes"),
    (12, "Diego Prado"),
]


def povoar():
    db.inicializar()
    db.limpar()

    for dados in ACERVO:
        livros.criar(dados)

    for livro_id, leitor in EMPRESTIMOS_INICIAIS:
        emprestimos.criar(livro_id, leitor)

    return len(ACERVO), len(EMPRESTIMOS_INICIAIS)


if __name__ == "__main__":
    total_de_livros, total_de_emprestimos = povoar()
    print(f"Banco povoado: {total_de_livros} livros e {total_de_emprestimos} empréstimos.")
    print(f"Arquivo: {db.CAMINHO_BANCO}")
