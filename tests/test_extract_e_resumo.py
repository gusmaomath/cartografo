"""Extração de corpo HTML, limpeza de texto, data Dynamo e truncamento ao LLM."""
from bs4 import BeautifulSoup

from cartografo.ai.resumo import _truncar
from cartografo.extract.html import extrair_corpo, limpar_texto
from cartografo.scrapers.dynamo import DynamoScraper


def test_extrair_corpo_remove_ruido_e_pega_paragrafos():
    html = """
    <html><body>
      <nav><p>menu</p></nav>
      <article><p>Primeiro parágrafo da carta.</p><p>Segundo parágrafo.</p></article>
      <footer><p>rodapé</p></footer>
    </body></html>
    """
    texto = extrair_corpo(BeautifulSoup(html, "lxml"), "article")
    assert "Primeiro parágrafo da carta." in texto
    assert "Segundo parágrafo." in texto
    assert "menu" not in texto and "rodapé" not in texto


def test_limpar_texto_normaliza_espacos_e_quebras():
    assert limpar_texto("a\r\n\n\n\nb   c\t\td") == "a\n\nb c d"


def test_dynamo_extrai_data_pt_br():
    data = DynamoScraper._extrair_data("Rio de Janeiro, 15 de março de 2025.")
    assert data is not None
    assert (data.year, data.month, data.day) == (2025, 3, 15)


def test_dynamo_sem_data_retorna_none():
    assert DynamoScraper._extrair_data("sem qualquer data aqui") is None


def test_truncar_respeita_limite_e_sinaliza():
    assert _truncar("abcdef", limite=0) == "abcdef"        # desligado
    assert _truncar("abc", limite=10) == "abc"             # abaixo do limite
    cortado = _truncar("abcdefghij", limite=4)
    assert cortado.startswith("abcd")
    assert "truncado" in cortado
