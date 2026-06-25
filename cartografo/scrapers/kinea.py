"""Scraper da Kinea — caso HTML (corpo da carta no slug do post)."""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..extract.html import extrair_corpo
from ..fetch.http import fetch_estatico
from ..schemas import DocumentoColetado
from .base import BaseScraper


class KineaScraper(BaseScraper):
    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        soup = BeautifulSoup(fetch_estatico(self.config.url_listagem), "lxml")
        url_post = self._primeiro_post(soup)
        if not url_post:
            self.log.warning("Nenhum post de carta encontrado na Kinea.")
            return None
        self.log.info("Post mais recente: %s", url_post)

        soup_post = BeautifulSoup(fetch_estatico(url_post), "lxml")
        titulo = soup_post.find("h1") or soup_post.find("title")
        titulo = titulo.get_text(strip=True) if titulo else "Carta do Gestor — Kinea"
        texto = self.limpar_texto(extrair_corpo(soup_post, self.config.seletor_corpo))

        return DocumentoColetado(
            gestora_slug=self.config.slug, titulo=titulo, url_documento=url_post,
            texto=texto, tipo="html",
        )

    def _primeiro_post(self, soup: BeautifulSoup) -> Optional[str]:
        for a in soup.select(self.config.seletor_link):
            href = a.get("href", "")
            if not href:
                continue
            url = urljoin(self.config.url_listagem, href)
            if "/blog/" in url and "categoria" not in url:
                return url
        return None
