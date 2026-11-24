acervo_sintetico = [
    ("Dom Casmurro", "Machado de Assis", 1899),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881),
    ("O Cortiço", "Aluísio Azevedo", 1890),
    ("Iracema", "José de Alencar", 1865),
    ("Senhora", "José de Alencar", 1875),
    ("Triste Fim de Policarpo Quaresma", "Lima Barreto", 1915),
    ("Os Sertões", "Euclides da Cunha", 1902),
    ("O Guarani", "José de Alencar", 1857),
    ("Quincas Borba", "Machado de Assis", 1891),
    ("A Moreninha", "Joaquim Manuel de Macedo", 1844),
    ("O Ateneu", "Raul Pompeia", 1888),
    ("Lucíola", "José de Alencar", 1862),
]

livros = {
    indice: {
        "id": indice,
        "titulo": titulo,
        "autor": autor,
        "ano": ano,
        "exemplares": 2 + indice % 4,
        "disponiveis": 1 + indice % 3,
    }
    for indice, (titulo, autor, ano) in enumerate(acervo_sintetico, start=1)
}
