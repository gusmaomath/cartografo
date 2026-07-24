"""Registry declarativo das fontes. Adicionar gestora = adicionar uma linha aqui."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Estrategia(str, Enum):
    HTML_ESTATICO = "html_estatico"   # httpx + BeautifulSoup
    HTML_DINAMICO = "html_dinamico"   # Playwright (SPA / JS)
    PDF = "pdf"                       # baixa PDF e extrai texto


@dataclass
class FonteConfig:
    slug: str
    nome: str
    url_listagem: str
    estrategia: Estrategia
    seletor_item: str = ""     # cada "card"/link de carta na listagem
    seletor_link: str = ""     # o <a> dentro do item
    seletor_corpo: str = ""    # corpo do artigo na página final (HTML)
    seletor_data: str = ""     # data de publicação, se houver
    ativo: bool = True
    base_url: str = ""           # origem para resolver links relativos (auto se vazio)
    prefere_pdf: bool = False    # dica: priorizar links .pdf na descoberta
    max_documentos: int = 3      # quantas cartas coletar por execução
    # Listagens adicionais da mesma gestora (ex.: uma página por fundo).
    paginas_extra: list[str] = field(default_factory=list)
    # Documentos em URL fixa (conteúdo muda a cada edição; dedup por hash).
    # Formato: {"titulo": ..., "url": ...}. Baixados sem etapa de descoberta.
    urls_diretas: list[dict] = field(default_factory=list)


REGISTRY: dict[str, FonteConfig] = {
    # --- Verificadas (listagem pública confirmada) -------------------------
    "dynamo": FonteConfig(
        slug="dynamo", nome="Dynamo",
        url_listagem="https://www.dynamo.com.br/pt/cartas-dynamo",
        estrategia=Estrategia.PDF,
        seletor_link='a[href*="/wp-content/uploads/"]',
    ),
    "kinea": FonteConfig(
        slug="kinea", nome="Kinea Investimentos",
        url_listagem="https://www.kinea.com.br/blog/categoria/carta-do-gestor/",
        estrategia=Estrategia.HTML_ESTATICO,
        seletor_item="article, .post, .card",
        seletor_link='a[href*="/blog/"]',
        seletor_corpo="article, .post-content, .entry-content, main",
    ),
    "kapitalo": FonteConfig(
        slug="kapitalo", nome="Kapitalo Investimentos",
        url_listagem="https://www.kapitalo.com.br/carta-do-gestor/kapa-e-zeta",
        estrategia=Estrategia.PDF, prefere_pdf=True, max_documentos=5,
        # Uma listagem por família de fundo — cartas diferentes por fundo.
        paginas_extra=[
            "https://www.kapitalo.com.br/carta-do-gestor/nw3",
            "https://www.kapitalo.com.br/carta-do-gestor/k10",
            "https://www.kapitalo.com.br/carta-do-gestor/tarkus",
            "https://www.kapitalo.com.br/carta-do-gestor/cartas-tematicas",
        ],
    ),
    "ip": FonteConfig(
        slug="ip", nome="IP Capital Partners",
        url_listagem="https://ip-capitalpartners.com/relatorios/",
        estrategia=Estrategia.HTML_ESTATICO,
        seletor_link='a[href*="/reports/"]',
        seletor_corpo="article, .report, .content, main",
    ),
    "bogari": FonteConfig(
        slug="bogari", nome="Bogari Capital",
        url_listagem="https://www.bogaricapital.com.br/cartas",
        estrategia=Estrategia.PDF, prefere_pdf=True,
    ),
    "squadra": FonteConfig(
        slug="squadra", nome="Squadra Investimentos",
        url_listagem="https://www.squadrainvest.com.br/cartas/",
        estrategia=Estrategia.PDF, prefere_pdf=True,
    ),
    "occam": FonteConfig(
        slug="occam", nome="Occam Brasil",
        url_listagem="https://occambrasil.com.br/cartas/",
        estrategia=Estrategia.PDF, prefere_pdf=True,
        max_documentos=4,  # série geral + série Crédito, 2 meses de cada
    ),
    "guepardo": FonteConfig(
        slug="guepardo", nome="Guepardo Investimentos",
        url_listagem="https://www.guepardoinvest.com.br/cartas",
        estrategia=Estrategia.PDF, prefere_pdf=True,
    ),
    "genoa": FonteConfig(
        slug="genoa", nome="Genoa Capital",
        # PDFs seguem padrão fixo /docs/CartaMensalGenoaCapital_<Mês><AA>.pdf
        url_listagem="https://www.genoacapital.com.br/docs/",
        estrategia=Estrategia.PDF, prefere_pdf=True,
    ),
    "atmos": FonteConfig(
        slug="atmos", nome="Atmos Capital",
        url_listagem="https://www.atmoscapital.com.br/documentos/cartas/",
        estrategia=Estrategia.PDF, prefere_pdf=True,
    ),
    "alaska": FonteConfig(
        slug="alaska", nome="Alaska Asset Management",
        url_listagem="https://www.alaska-asset.com.br/cartas/",
        estrategia=Estrategia.HTML_DINAMICO, prefere_pdf=True,
    ),
    "dahlia": FonteConfig(
        slug="dahlia", nome="Dahlia Capital",
        url_listagem="https://www.dahliacapital.com.br/nossas-cartas",
        estrategia=Estrategia.HTML_DINAMICO,
        # Wix: cartas são posts de blog sem palavra-chave no slug.
        seletor_link='a[href*="/post/"]',
        seletor_corpo="article, main",
    ),
    "ibiuna": FonteConfig(
        slug="ibiuna", nome="Ibiuna Investimentos",
        url_listagem="https://www.ibiunainvest.com.br/fundos/",
        estrategia=Estrategia.HTML_ESTATICO, prefere_pdf=True, max_documentos=6,
        # Relatórios mensais por fundo em URL estável (conteúdo muda por edição).
        urls_diretas=[
            {"titulo": "Relatório Mensal — Ibiuna Hedge STH FIC FIM",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaHedgeSTHFICFIM.pdf"},
            {"titulo": "Relatório Mensal — Ibiuna Hedge FIC FIM",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaHedgeFICFIM.pdf"},
            {"titulo": "Relatório Mensal — Ibiuna Previdência FIC FIM",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaPrevidenciaFICFIM.pdf"},
            {"titulo": "Relatório Mensal — Ibiuna Long Short STLS FIC FIM",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaLongShortSTLSFICFIM.pdf"},
            {"titulo": "Relatório Mensal — Ibiuna Equities FIC FIA",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaEquitiesFICFIA.pdf"},
            {"titulo": "Relatório Mensal — Ibiuna Long Biased FIC FIM",
             "url": "https://www.ibiunainvest.com.br/wp-content/uploads/fundos/RelatorioMensal_IbiunaLongBiasedFICFIM.pdf"},
        ],
    ),
    # --- Catalogadas (listagem ainda não confirmada / anti-bot) ------------
    "spx":           FonteConfig("spx", "SPX Capital", "https://www.spxcapital.com/pt-br/", Estrategia.HTML_DINAMICO),
    "btg":           FonteConfig("btg", "BTG Pactual Asset", "https://asset.btgpactual.com/insights", Estrategia.HTML_DINAMICO),
    "verde":         FonteConfig("verde", "Verde Asset", "https://www.verdeasset.com.br/", Estrategia.HTML_DINAMICO),
    "constellation": FonteConfig("constellation", "Constellation", "https://www.constellation.com.br/pt-br/cartas", Estrategia.HTML_DINAMICO),
    "jgp":           FonteConfig("jgp", "JGP", "https://jgp.com.br/analises", Estrategia.HTML_DINAMICO),
    "legacy":        FonteConfig("legacy", "Legacy Capital", "https://legacycapital.com.br/", Estrategia.HTML_DINAMICO, prefere_pdf=True),
    "gavea":         FonteConfig("gavea", "Gávea Investimentos", "https://www.gaveainvestimentos.com.br/imprensa-publicacoes", Estrategia.HTML_ESTATICO),
    "absolute":      FonteConfig("absolute", "Absolute Investimentos", "https://absoluteinvestimentos.com.br/fundos/", Estrategia.HTML_DINAMICO, prefere_pdf=True),
    "mar":           FonteConfig("mar", "Mar Asset Management", "https://www.marasset.com.br/", Estrategia.HTML_DINAMICO, prefere_pdf=True),
    "vista":         FonteConfig("vista", "Vista Capital", "https://vistacapital.com.br/fundos/", Estrategia.HTML_DINAMICO, prefere_pdf=True),
    "giant":         FonteConfig("giant", "Giant Steps Capital", "https://gscap.com.br/artigos/", Estrategia.HTML_DINAMICO, max_documentos=4,
                                 seletor_link='a[href*="carta"]'),
    "realinvestor":  FonteConfig("realinvestor", "Real Investor", "https://www.realinvestor.com.br/cartas", Estrategia.PDF, prefere_pdf=True),
    "capitania":     FonteConfig("capitania", "Capitânia Investimentos", "https://www.capitania.net/relatorios/", Estrategia.HTML_DINAMICO, prefere_pdf=True),
    "vinci":         FonteConfig("vinci", "Vinci Partners", "https://www.vincipartners.com", Estrategia.HTML_DINAMICO),
    "xpasset":       FonteConfig("xpasset", "XP Asset Management", "https://www.xpasset.com.br/materiais", Estrategia.HTML_DINAMICO),
    "agora":         FonteConfig("agora", "Ágora Investimentos", "https://insights.agorainvestimentos.com.br", Estrategia.HTML_DINAMICO),
    "bram":          FonteConfig("bram", "Bradesco Asset (BRAM)", "https://www.bradescoasset.com.br", Estrategia.HTML_DINAMICO),
}
