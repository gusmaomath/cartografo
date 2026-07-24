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
        docs = self.coletar()
        return docs[0] if docs else None

    def coletar(self) -> list[DocumentoColetado]:
        soup = BeautifulSoup(fetch_estatico(self.config.url_listagem), "lxml")
        posts = self._posts(soup)
        if not posts:
            self.log.warning("Nenhum post de carta encontrado na Kinea.")
            return []

        docs = []
        for url_post in posts[: self.config.max_documentos]:
            self.log.info("Coletando post: %s", url_post)
            try:
                soup_post = BeautifulSoup(fetch_estatico(url_post), "lxml")
            except Exception as exc:  # noqa: BLE001
                self.log.warning("Falha ao baixar %s: %s", url_post, exc)
                continue
            titulo = soup_post.find("h1") or soup_post.find("title")
            titulo = titulo.get_text(strip=True) if titulo else "Carta do Gestor — Kinea"
            texto = self.limpar_texto(extrair_corpo(soup_post, self.config.seletor_corpo))
            docs.append(DocumentoColetado(
                gestora_slug=self.config.slug, titulo=titulo, url_documento=url_post,
                texto=texto, tipo="html",
            ))
        return docs

    def _posts(self, soup: BeautifulSoup) -> list[str]:
        urls, vistos = [], set()
        for a in soup.select(self.config.seletor_link):
            href = a.get("href", "")
            if not href:
                continue
            url = urljoin(self.config.url_listagem, href)
            if "/blog/" in url and "categoria" not in url and url not in vistos:
                vistos.add(url)
                urls.append(url)
        return urls
