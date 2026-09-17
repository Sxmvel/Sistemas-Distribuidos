import pytest

from app import topicos


def test_montar_segue_a_hierarquia_da_taxonomia():
    assert (
        topicos.montar("central", "term-01", topicos.EMPRESTIMO)
        == "biblioteca/central/term-01/emprestimo"
    )


def test_topico_de_status_usa_o_nivel_reservado():
    assert topicos.de_status("anexo", "term-03") == "biblioteca/anexo/term-03/status"


def test_evento_fora_da_taxonomia_e_rejeitado():
    with pytest.raises(topicos.TopicoInvalido, match="evento desconhecido"):
        topicos.montar("central", "term-01", "reserva")


@pytest.mark.parametrize("valor", ["a/b", "a+b", "a#b"])
def test_nivel_com_separador_ou_wildcard_e_rejeitado(valor):
    with pytest.raises(topicos.TopicoInvalido):
        topicos.montar(valor, "term-01", topicos.EMPRESTIMO)


def test_nivel_vazio_e_rejeitado():
    with pytest.raises(topicos.TopicoInvalido, match="não pode ser vazio"):
        topicos.montar("central", "", topicos.EMPRESTIMO)


def test_decompor_devolve_os_quatro_niveis():
    assert topicos.decompor("biblioteca/central/term-01/emprestimo") == {
        "raiz": "biblioteca",
        "unidade": "central",
        "terminal": "term-01",
        "evento": "emprestimo",
    }


@pytest.mark.parametrize(
    "topico",
    ["biblioteca/central/term-01", "outra/central/term-01/emprestimo", "biblioteca"],
)
def test_decompor_rejeita_topico_fora_da_taxonomia(topico):
    with pytest.raises(topicos.TopicoInvalido, match="fora da taxonomia"):
        topicos.decompor(topico)


def test_atalhos_de_nivel():
    topico = "biblioteca/anexo/term-03/devolucao"
    assert topicos.unidade_de(topico) == "anexo"
    assert topicos.terminal_de(topico) == "term-03"
    assert topicos.evento_de(topico) == "devolucao"


class TestWildcards:
    def test_mais_substitui_exatamente_um_nivel(self):
        assert topicos.casa_com(
            "biblioteca/+/+/emprestimo", "biblioteca/central/term-01/emprestimo"
        )

    def test_mais_nao_atravessa_niveis(self):
        assert not topicos.casa_com(
            "biblioteca/+/emprestimo", "biblioteca/central/term-01/emprestimo"
        )

    def test_mais_nao_casa_com_outro_evento(self):
        assert not topicos.casa_com(
            "biblioteca/+/+/emprestimo", "biblioteca/central/term-01/status"
        )

    def test_cerquilha_cobre_os_niveis_restantes(self):
        assert topicos.casa_com("biblioteca/#", "biblioteca/central/term-01/status")

    def test_cerquilha_no_meio_da_hierarquia(self):
        assert topicos.casa_com("biblioteca/central/#", "biblioteca/central/term-01/devolucao")
        assert not topicos.casa_com("biblioteca/anexo/#", "biblioteca/central/term-01/devolucao")

    def test_topico_exato_casa_consigo_mesmo(self):
        topico = "biblioteca/central/term-01/status"
        assert topicos.casa_com(topico, topico)

    def test_filtro_de_emprestimos_ignora_status(self):
        assert not topicos.casa_com(
            topicos.FILTRO_DE_EMPRESTIMOS, "biblioteca/central/term-01/status"
        )

    def test_filtro_de_tudo_alcanca_todos_os_eventos(self):
        for evento in topicos.EVENTOS:
            topico = topicos.montar("central", "term-01", evento)
            assert topicos.casa_com(topicos.FILTRO_DE_TUDO, topico)
