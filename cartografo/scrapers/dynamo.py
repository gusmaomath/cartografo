"""Scraper da Dynamo — caso PDF (WordPress, PDFs em /wp-content/uploads/)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..extract.pdf import extrair_texto_pdf
from ..fetch.http import fetch_binario, fetch_estatico
from ..schemas import DocumentoColetado
from .base import BaseScraper

_MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
          "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


class DynamoScraper(BaseScraper):
    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        html = fetch_estatico(self.config.url_listagem)
        soup = BeautifulSoup(html, "lxml")

        pdfs = [
            urljoin(self.config.url_listagem, a["href"])
            for a in soup.select(self.config.seletor_link)
            if a.get("href", "").lower().endswith(".pdf")
        ]
        if not pdfs:
            self.log.warning("Nenhum PDF encontrado na listagem da Dynamo.")
            return None

        url_pdf = pdfs[0]  # ordem do documento = mais recente no topo
        self.log.info("PDF mais recente: %s", url_pdf)

        titulo = self._inferir_titulo(soup, url_pdf)
        texto = self.limpar_texto(extrair_texto_pdf(fetch_binario(url_pdf)))

        return DocumentoColetado(
            gestora_slug=self.config.slug, titulo=titulo, url_documento=url_pdf,
            texto=texto, tipo="pdf", data_publicacao=self._extrair_data(texto),
        )

    def _inferir_titulo(self, soup: BeautifulSoup, url_pdf: str) -> str:
        for a in soup.find_all("a", href=True):
            if a["href"] in url_pdf or url_pdf.endswith(a["href"]):
                txt = a.get_text(strip=True)
                if txt:
                    return txt
        nome = urlparse(url_pdf).path.split("/")[-1]
        return f"Carta Dynamo ({nome})"

    @staticmethod
    def _extrair_data(texto: str) -> Optional[datetime]:
        m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto.lower())
        if m and m.group(2) in _MESES:
            return datetime(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
        return None
