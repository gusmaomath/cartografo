"""
Scraper genérico guiado por heurística. Cobre qualquer gestora sem código
dedicado, com cascata de fallbacks de coleta e extração. Coleta múltiplos
documentos por fonte (uma carta por fundo/série quando a listagem tem várias)
e varre também as `paginas_extra` configuradas no registry.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from ..extract.descoberta import descobrir_documentos
from ..extract.html import extrair_corpo
from ..extract.pdf import extrair_texto_pdf
from ..fetch.resilient import obter_html_dinamico, obter_listagem, obter_resposta
from ..registry import Estrategia
from ..schemas import DocumentoColetado
from .base import BaseScraper

_CORPO_PADRAO = "article, .post-content, .entry-content, .content, main"
_TITULOS_GENERICOS = ("baixar pdf", "baixar", "download", "leia aqui", "leia mais",
                      "clique aqui", "acesse", "ver carta", "abrir", "pdf", "ver mais")


def _titulo_do_arquivo(url: str) -> str:
    nome = unquote(urlparse(url).path.split("/")[-1])
    nome = re.sub(r"\.pdf$", "", nome, flags=re.I)
    return re.sub(r"[-_]+", " ", nome).strip() or url


class GenericScraper(BaseScraper):
    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        docs = self.coletar(limite_total=1)
        return docs[0] if docs else None

    def coletar(self, limite_total: int | None = None) -> list[DocumentoColetado]:
        dinamico = self.config.estrategia == Estrategia.HTML_DINAMICO
        limite = limite_total or self.config.max_documentos

        # 0) Documentos em URL fixa (ex.: relatório mensal por fundo) — sem
        # descoberta; a troca de edição é detectada pelo dedup de hash.
        docs: list[DocumentoColetado] = []
        for direto in self.config.urls_diretas[:limite]:
            try:
                doc = self._coletar_conteudo(direto["url"], direto["titulo"], dinamico)
            except Exception as exc:  # noqa: BLE001
                self.log.warning("URL direta falhou (%s): %s", direto["url"], exc)
                continue
            if doc and len(doc.texto) >= 120:
                docs.append(doc)
        if len(docs) >= limite:
            return docs

        # Candidatos de todas as listagens (principal + uma por fundo, se houver)
        paginas = [self.config.url_listagem] + list(self.config.paginas_extra)
        por_pagina = limite if len(paginas) == 1 else max(2, limite // len(paginas) + 1)

        por_listagem: list[list[dict]] = []
        for pagina in paginas:
            try:
                html, estrat = obter_listagem(
                    pagina, dinamico=dinamico,
                    espera_seletor=self.config.seletor_item or None)
                self.log.info("Listagem %s via '%s'", pagina, estrat)
            except Exception as exc:  # noqa: BLE001 - uma listagem não derruba as demais
                self.log.warning("Listagem %s falhou: %s", pagina, exc)
                continue
            por_listagem.append(descobrir_documentos(
                html, self.config, limite=por_pagina, url_base=pagina))

        # Round-robin entre as listagens: garante a carta mais recente de CADA
        # fundo antes de aprofundar no histórico de um único.
        candidatos: list[dict] = []
        vistos: set[str] = set()
        for rodada in range(por_pagina):
            for achados in por_listagem:
                if rodada < len(achados) and achados[rodada]["url"] not in vistos:
                    vistos.add(achados[rodada]["url"])
                    candidatos.append(achados[rodada])

        if not candidatos:
            if not docs:
                self.log.warning("Nenhum documento candidato encontrado nas listagens.")
            return docs

        urls_ja_coletadas = {d.url_documento for d in docs}
        candidatos = [c for c in candidatos if c["url"] not in urls_ja_coletadas]
        for achado in candidatos[: limite * 2]:  # folga p/ candidatos que falham
            if len(docs) >= limite:
                break
            self.log.info("Candidato (score=%s): %s", achado["score"], achado["url"])
            try:
                doc = self._coletar_conteudo(achado["url"], achado["titulo"], dinamico)
            except Exception as exc:  # noqa: BLE001 - segue para o próximo candidato
                self.log.warning("Falha ao coletar %s: %s", achado["url"], exc)
                continue
            if doc and len(doc.texto) >= 120:
                docs.append(doc)
        return docs

    def _coletar_conteudo(self, url: str, titulo: str, dinamico: bool) -> Optional[DocumentoColetado]:
        resp = obter_resposta(url)
        conteudo = resp.content
        ctype = resp.headers.get("content-type", "").lower()
        eh_pdf = conteudo[:4] == b"%PDF" or "application/pdf" in ctype or url.lower().endswith(".pdf")

        if eh_pdf:
            texto = extrair_texto_pdf(conteudo)
            tipo = "pdf"
            if not titulo or titulo.strip().lower() in _TITULOS_GENERICOS:
                titulo = _titulo_do_arquivo(url)
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
