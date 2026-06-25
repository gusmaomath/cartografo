"""Limpeza e extração de texto a partir de HTML."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

_RUIDO = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\r", "\n", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_corpo(soup: BeautifulSoup, seletor_corpo: str) -> str:
    """Remove ruído estrutural e extrai os parágrafos do container alvo."""
    for tag in soup(_RUIDO):
        tag.decompose()
    container = soup.select_one(seletor_corpo) if seletor_corpo else None
    alvo = container if container else soup
    paragrafos = [p.get_text(" ", strip=True) for p in alvo.find_all("p")]
    return "\n\n".join(p for p in paragrafos if len(p) > 1)
