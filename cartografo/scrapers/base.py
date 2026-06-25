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

    @staticmethod
    def limpar_texto(texto: str) -> str:
        return limpar_texto(texto)
