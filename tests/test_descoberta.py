"""Descoberta heurística do documento mais recente."""
from cartografo.extract.descoberta import descobrir_documento
from cartografo.registry import Estrategia, FonteConfig


def _cfg(**kw) -> FonteConfig:
    base = dict(slug="x", nome="X", url_listagem="https://exemplo.com/cartas",
                estrategia=Estrategia.HTML_ESTATICO)
    base.update(kw)
    return FonteConfig(**base)


def test_prefere_link_de_carta_a_ruido_de_menu():
    html = """
    <a href="/sobre">Sobre nós</a>
    <a href="/cartas/carta-maio-2025">Carta do Gestor — Maio 2025</a>
    <a href="/contato">Contato</a>
    """
    achado = descobrir_documento(html, _cfg())
    assert achado is not None
    assert achado["url"].endswith("/cartas/carta-maio-2025")


def test_pdf_ganha_bonus_em_fonte_pdf():
    html = """
    <a href="/blog/post-html">Comentário mensal</a>
    <a href="/uploads/relatorio-2025.pdf">Relatório 2025</a>
    """
    achado = descobrir_documento(html, _cfg(estrategia=Estrategia.PDF))
    assert achado["url"].endswith(".pdf")
    assert achado["eh_pdf"] is True


def test_desempate_por_ordem_no_documento():
    # Mesmo score; o primeiro no documento (mais recente) deve vencer.
    html = """
    <a href="/cartas/carta-2025-junho">Carta Junho 2025</a>
    <a href="/cartas/carta-2025-maio">Carta Maio 2025</a>
    """
    achado = descobrir_documento(html, _cfg())
    assert achado["url"].endswith("carta-2025-junho")


def test_sem_candidato_retorna_none():
    achado = descobrir_documento('<a href="#">topo</a><a href="mailto:a@b.c">email</a>', _cfg())
    assert achado is None


def test_ignora_esquemas_nao_http():
    html = '<a href="javascript:void(0)">x</a><a href="/cartas/carta-relatorio-2025">Carta relatório 2025</a>'
    achado = descobrir_documento(html, _cfg())
    assert achado["url"].startswith("https://")
