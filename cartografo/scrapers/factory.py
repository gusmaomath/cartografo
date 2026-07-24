"""Resolve slug -> scraper. Concretos têm prioridade; senão usa o genérico."""
from __future__ import annotations

from ..registry import REGISTRY
from .base import BaseScraper
from .dynamo import DynamoScraper
from .generico import GenericScraper
from .genoa import GenoaScraper
from .kinea import KineaScraper

# Scrapers concretos (sobrescrevem o genérico quando registrados).
SCRAPERS: dict[str, type[BaseScraper]] = {
    "dynamo": DynamoScraper,
    "kinea": KineaScraper,
    "genoa": GenoaScraper,
}


def get_scraper(slug: str) -> BaseScraper:
    config = REGISTRY[slug]
    classe = SCRAPERS.get(slug, GenericScraper)
    return classe(config)
