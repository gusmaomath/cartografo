"""Descoberta heurística do documento mais recente numa página de listagem."""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..registry import Estrategia, FonteConfig

log = logging.getLogger("cartografo.descoberta")

# Sinais textuais de que um link aponta para uma carta/relatório.
PALAVRAS = ["carta", "relatóri", "relatori", "gestor", "mensal", "trimestral",
            "publicac", "insight", "material", "documento", "comentári", "comentari",
            "cenári", "cenari", "análise", "analise", "perspectiv"]
MESES = ["janeiro", "fevereiro", "março", "marco", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
ANOS = ["2024", "2025", "2026", "2027"]
IGNORAR_PREFIXOS = ("#", "mailto:", "tel:", "javascript:")


def _eh_pdf(url: str) -> bool:
    u = url.lower()
    return u.endswith(".pdf") or ".pdf?" in u


def _pontuar(url: str, texto: str, config: FonteConfig, bonus: int) -> int:
    alvo = f"{texto} {url}".lower()
    score = bonus
    if _eh_pdf(url):
        score += 5
    if any(p in alvo for p in PALAVRAS):
        score += 3
    if any(m in alvo for m in MESES):
        score += 2
    if any(a in alvo for a in ANOS):
        score += 2
    prefere_pdf = config.prefere_pdf or config.estrategia == Estrategia.PDF
    if prefere_pdf and not _eh_pdf(url):
        score -= 2
    return score


def descobrir_documento(html: str, config: FonteConfig) -> Optional[dict]:
    """
    Retorna {url, titulo, eh_pdf, score} do melhor candidato, ou None.
    Cascata: seletor configurado (bônus alto) → varredura heurística de todos os <a>.
    """
    soup = BeautifulSoup(html, "lxml")
    melhores: dict[str, tuple] = {}  # url -> (score, ordem, titulo)

    # Ordem canônica = posição do link no documento (mais recente costuma estar
    # no topo). Calculada num único scan para que o desempate seja estável
    # independente de qual passada (seletor ou varredura) definiu o score.
    ordem_doc: dict[str, int] = {}
    for i, a in enumerate(soup.find_all("a", href=True)):
        url = urljoin(config.url_listagem, (a.get("href") or "").strip())
        ordem_doc.setdefault(url, i)

    def considerar(anchors, bonus):
        for a in anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(IGNORAR_PREFIXOS):
                continue
            url = urljoin(config.url_listagem, href)
            if urlparse(url).scheme not in ("http", "https"):
                continue
            texto = a.get_text(" ", strip=True)
            score = _pontuar(url, texto, config, bonus)
            if score < 3:  # corta ruído de menu/rodapé
                continue
            atual = melhores.get(url)
            if atual is None or score > atual[0]:
                titulo = texto or urlparse(url).path.split("/")[-1]
                melhores[url] = (score, ordem_doc.get(url, 10**9), titulo)

    if config.seletor_link:
        considerar(soup.select(config.seletor_link), bonus=8)
    considerar(soup.find_all("a", href=True), bonus=0)

    if not melhores:
        return None
    # maior score; empate → menor ordem (mais recente costuma estar no topo)
    url, (score, _ordem, titulo) = min(
        melhores.items(), key=lambda kv: (-kv[1][0], kv[1][1]))
    return {"url": url, "titulo": titulo, "eh_pdf": _eh_pdf(url), "score": score}
