"""Registry declarativo das fontes. Adicionar gestora = adicionar uma linha aqui."""
from __future__ import annotations

from dataclasses import dataclass
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


REGISTRY: dict[str, FonteConfig] = {
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
    # --- Catalogadas para implementação incremental ------------------------
    "spx":           FonteConfig("spx", "SPX Capital", "https://spxcapital.com/pt-br/midia-e-documentos", Estrategia.HTML_DINAMICO),
    "btg":           FonteConfig("btg", "BTG Pactual Asset", "https://asset.btgpactual.com/insights", Estrategia.HTML_DINAMICO),
    "verde":         FonteConfig("verde", "Verde Asset", "https://www.verdeasset.com.br/publicacoes", Estrategia.HTML_DINAMICO),
    "kapitalo":      FonteConfig("kapitalo", "Kapitalo", "https://www.kapitalo.com.br/cartas", Estrategia.PDF),
    "ibiuna":        FonteConfig("ibiuna", "Ibiuna Investimentos", "https://www.ibiunainvestimentos.com.br/publicacoes", Estrategia.HTML_ESTATICO),
    "constellation": FonteConfig("constellation", "Constellation", "https://www.constellation.com.br/pt-br/cartas", Estrategia.HTML_DINAMICO),
    "ip":            FonteConfig("ip", "IP Capital Partners", "https://ipcapitalpartners.com/cartas", Estrategia.PDF),
    "jgp":           FonteConfig("jgp", "JGP", "https://jgp.com.br/analises", Estrategia.HTML_DINAMICO),
    "legacy":        FonteConfig("legacy", "Legacy Capital", "https://www.legacycapital.com.br/publicacoes", Estrategia.PDF),
    "gavea":         FonteConfig("gavea", "Gávea Investimentos", "https://www.gaveainvestimentos.com.br/imprensa-publicacoes", Estrategia.HTML_ESTATICO),
    "bogari":        FonteConfig("bogari", "Bogari Capital", "https://www.bogaricapital.com.br/cartas", Estrategia.PDF),
    "absolute":      FonteConfig("absolute", "Absolute Investimentos", "https://www.absoluteinvestimentos.com.br/documentos", Estrategia.HTML_ESTATICO),
    "agora":         FonteConfig("agora", "Ágora Investimentos", "https://insights.agorainvestimentos.com.br", Estrategia.HTML_DINAMICO),
    "bram":          FonteConfig("bram", "Bradesco Asset (BRAM)", "https://www.bradescoasset.com.br", Estrategia.HTML_DINAMICO),
    "giant":         FonteConfig("giant", "Giant Steps Capital", "https://giantsteps.com.br/conteudos", Estrategia.HTML_ESTATICO),
    "realinvestor":  FonteConfig("realinvestor", "Real Investor", "https://www.realinvestor.com.br/cartas", Estrategia.PDF),
    "capitania":     FonteConfig("capitania", "Trítono / Capitânia", "https://www.capitaniainvestimentos.com.br/relatorios", Estrategia.HTML_DINAMICO),
    "vinci":         FonteConfig("vinci", "Vinci Partners", "https://www.vincipartners.com", Estrategia.HTML_DINAMICO),
    "xpasset":       FonteConfig("xpasset", "XP Asset Management", "https://www.xpasset.com.br/materiais", Estrategia.HTML_DINAMICO),
}
