"""Descoberta heurística do documento mais recente."""
from cartografo.extract.descoberta import descobrir_documento, descobrir_documentos
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


def test_multiplos_candidatos_ordenados_e_limitados():
    html = """
    <a href="/cartas/carta-2025-junho">Carta Junho 2025</a>
    <a href="/cartas/carta-2025-maio">Carta Maio 2025</a>
    <a href="/cartas/carta-2025-abril">Carta Abril 2025</a>
    <a href="/sobre">Sobre nós</a>
    """
    achados = descobrir_documentos(html, _cfg(), limite=2)
    assert [a["url"].rsplit("-", 1)[-1] for a in achados] == ["junho", "maio"]


def test_url_base_resolve_links_de_pagina_extra():
    html = '<a href="doc/carta-mensal-2025.pdf">Carta mensal 2025</a>'
    achados = descobrir_documentos(
        html, _cfg(), url_base="https://exemplo.com/fundos/zeta/")
    assert achados[0]["url"] == "https://exemplo.com/fundos/zeta/doc/carta-mensal-2025.pdf"


def test_recencia_por_ano_vence_ordem_da_pagina():
    # Página lista do mais antigo para o mais novo; o ano deve desempatar.
    html = """
    <a href="/Carta-84-Carta-aos-Investidores-Abr18.pdf">Carta 84 Abr18</a>
    <a href="/Carta-116-Carta-aos-Investidores-4T25.pdf">Carta 116 4T25</a>
    """
    achados = descobrir_documentos(html, _cfg(estrategia=Estrategia.PDF))
    assert "4T25" in achados[0]["url"]


def test_penaliza_documento_institucional():
    html = """
    <a href="/docs/politica_privacidade.pdf">Política de Privacidade</a>
    <a href="/docs/carta-mensal-junho-2025.pdf">Carta Mensal Junho 2025</a>
    """
    achados = descobrir_documentos(html, _cfg(estrategia=Estrategia.PDF))
    assert all("privacidade" not in a["url"] for a in achados)


def test_ignora_esquemas_nao_http():
    html = '<a href="javascript:void(0)">x</a><a href="/cartas/carta-relatorio-2025">Carta relatório 2025</a>'
    achado = descobrir_documento(html, _cfg())
    assert achado["url"].startswith("https://")
