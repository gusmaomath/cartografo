"""Contrato comum dos scrapers."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..extract.html import limpar_texto
from ..registry import FonteConfig
from ..schemas import DocumentoColetado


class BaseScraper(ABC):
    def __init__(self, config: FonteConfig):
        self.config = config
        self.log = logging.getLogger(f"cartografo.{config.slug}")

    @abstractmethod
    def coletar_mais_recente(self) -> Optional[DocumentoColetado]:
        ...

    def coletar(self) -> list[DocumentoColetado]:
        """
        Coleta até `config.max_documentos` cartas da fonte (a mais recente de
        cada fundo/série quando houver várias). Implementação padrão devolve
        apenas a mais recente; scrapers multi-documento sobrescrevem.
        """
        doc = self.coletar_mais_recente()
        return [doc] if doc else []

    @staticmethod
    def limpar_texto(texto: str) -> str:
        return limpar_texto(texto)
