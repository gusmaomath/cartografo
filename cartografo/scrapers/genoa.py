"""
Scraper da Genoa Capital — o site é SPA sem listagem estática, mas os PDFs
seguem padrão estável: /docs/CartaMensalGenoaCapital_<Mmm><AA>.pdf
(ex.: CartaMensalGenoaCapital_Jun26.pdf). Testa do mês atual para trás.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..config import agora_utc
from ..extract.pdf import extrair_texto_pdf
from ..fetch.http import fetch_binario
from ..schemas import DocumentoColetado
from .base import BaseScraper

_MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
_MESES_NOME = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
               "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


class GenoaScraper(BaseScraper):
    MESES_RETROATIVOS = 6  # até onde procurar carta publicada

    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        docs = self.coletar()
        return docs[0] if docs else None

    def coletar(self) -> list[DocumentoColetado]:
        hoje = agora_utc()
        ano, mes = hoje.year, hoje.month
        docs: list[DocumentoColetado] = []

        for _ in range(self.MESES_RETROATIVOS):
            url = (f"{self.config.url_listagem.rstrip('/')}/"
                   f"CartaMensalGenoaCapital_{_MESES_ABREV[mes - 1]}{ano % 100:02d}.pdf")
            try:
                conteudo = fetch_binario(url)
                if conteudo[:4] == b"%PDF":
                    texto = self.limpar_texto(extrair_texto_pdf(conteudo))
                    if len(texto) >= 120:
                        self.log.info("Carta encontrada: %s", url)
                        docs.append(DocumentoColetado(
                            gestora_slug=self.config.slug,
                            titulo=f"Carta Mensal Genoa Capital — {_MESES_NOME[mes - 1]} {ano}",
                            url_documento=url, texto=texto, tipo="pdf",
                            data_publicacao=datetime(ano, mes, 1),
                        ))
            except Exception:  # noqa: BLE001 - mês sem carta publicada ainda
                self.log.info("Sem carta em %s/%s; tentando mês anterior.", mes, ano)
            if len(docs) >= self.config.max_documentos:
                break
            mes -= 1
            if mes == 0:
                mes, ano = 12, ano - 1
        if not docs:
            self.log.warning("Nenhuma carta Genoa encontrada nos últimos %d meses.",
                             self.MESES_RETROATIVOS)
        return docs
