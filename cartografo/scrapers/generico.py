"""
Scraper genérico guiado por heurística. Cobre qualquer gestora sem código
dedicado, com cascata de fallbacks de coleta e extração. Scrapers concretos
(Dynamo, Kinea) têm prioridade quando registrados.
"""
from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup

from ..extract.descoberta import descobrir_documento
from ..extract.html import extrair_corpo
from ..extract.pdf import extrair_texto_pdf
from ..fetch.resilient import obter_html_dinamico, obter_listagem, obter_resposta
from ..registry import Estrategia
from ..schemas import DocumentoColetado
from .base import BaseScraper

_CORPO_PADRAO = "article, .post-content, .entry-content, .content, main"


class GenericScraper(BaseScraper):
    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        dinamico = self.config.estrategia == Estrategia.HTML_DINAMICO

        # 1) Listagem (estático↔dinâmico com fallback)
        html, estrat = obter_listagem(
            self.config.url_listagem, dinamico=dinamico,
            espera_seletor=self.config.seletor_item or None)
        self.log.info("Listagem via '%s'", estrat)

        # 2) Descoberta do documento mais recente
        achado = descobrir_documento(html, self.config)
        if not achado:
            self.log.warning("Nenhum documento candidato encontrado na listagem.")
            return None
        self.log.info("Candidato (score=%s): %s", achado["score"], achado["url"])

        # 3) Conteúdo, com detecção robusta de tipo (magic bytes) e fallbacks
        return self._coletar_conteudo(achado["url"], achado["titulo"], dinamico)

    def _coletar_conteudo(self, url: str, titulo: str, dinamico: bool) -> Optional[DocumentoColetado]:
        resp = obter_resposta(url)
        conteudo = resp.content
        ctype = resp.headers.get("content-type", "").lower()
        eh_pdf = conteudo[:4] == b"%PDF" or "application/pdf" in ctype or url.lower().endswith(".pdf")

        if eh_pdf:
            texto = extrair_texto_pdf(conteudo)
            tipo = "pdf"
        else:
            soup = BeautifulSoup(resp.text, "lxml")
            h1 = soup.find("h1") or soup.find("title")
            if h1 and h1.get_text(strip=True):
                titulo = h1.get_text(strip=True)
            texto = extrair_corpo(soup, self.config.seletor_corpo or _CORPO_PADRAO)
            # fallback: corpo curto numa fonte dinâmica → renderiza com Playwright
            if len(texto) < 200 and dinamico:
                self.log.info("Corpo curto; escalando para renderização dinâmica.")
                try:
                    soup = BeautifulSoup(obter_html_dinamico(url), "lxml")
                    texto = extrair_corpo(soup, self.config.seletor_corpo or _CORPO_PADRAO)
                except Exception as exc:  # noqa: BLE001
                    self.log.warning("Renderização dinâmica falhou: %s", exc)
            tipo = "html"

        texto = self.limpar_texto(texto)
        if len(texto) < 120:
            self.log.warning("Texto final muito curto (%d chars) para %s", len(texto), url)
        return DocumentoColetado(
            gestora_slug=self.config.slug, titulo=titulo, url_documento=url,
            texto=texto, tipo=tipo,
        )
