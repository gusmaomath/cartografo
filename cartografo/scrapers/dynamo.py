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
        docs = self.coletar()
        return docs[0] if docs else None

    def coletar(self) -> list[DocumentoColetado]:
        html = fetch_estatico(self.config.url_listagem)
        soup = BeautifulSoup(html, "lxml")

        pdfs, vistos = [], set()
        for a in soup.select(self.config.seletor_link):
            url = urljoin(self.config.url_listagem, a.get("href", ""))
            if url.lower().endswith(".pdf") and url not in vistos:
                vistos.add(url)
                pdfs.append(url)
        if not pdfs:
            self.log.warning("Nenhum PDF encontrado na listagem da Dynamo.")
            return []

        docs = []
        for url_pdf in pdfs[: self.config.max_documentos]:  # topo = mais recente
            self.log.info("Coletando PDF: %s", url_pdf)
            try:
                texto = self.limpar_texto(extrair_texto_pdf(fetch_binario(url_pdf)))
            except Exception as exc:  # noqa: BLE001
                self.log.warning("Falha ao extrair %s: %s", url_pdf, exc)
                continue
            docs.append(DocumentoColetado(
                gestora_slug=self.config.slug,
                titulo=self._inferir_titulo(soup, url_pdf), url_documento=url_pdf,
                texto=texto, tipo="pdf", data_publicacao=self._extrair_data(texto),
            ))
        return docs

    _TITULOS_GENERICOS = ("leia aqui", "leia mais", "download", "baixar",
                          "clique aqui", "acesse", "ver carta", "abrir")

    def _inferir_titulo(self, soup: BeautifulSoup, url_pdf: str) -> str:
        for a in soup.find_all("a", href=True):
            if a["href"] in url_pdf or url_pdf.endswith(a["href"]):
                txt = a.get_text(strip=True)
                if txt and txt.lower() not in self._TITULOS_GENERICOS:
                    return txt
        nome = urlparse(url_pdf).path.split("/")[-1]
        nome = re.sub(r"\.pdf$", "", nome, flags=re.I).replace("-", " ").replace("_", " ")
        return nome if "dynamo" in nome.lower() else f"Carta Dynamo ({nome})"

    @staticmethod
    def _extrair_data(texto: str) -> Optional[datetime]:
        m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto.lower())
        if m and m.group(2) in _MESES:
            return datetime(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
        return None
