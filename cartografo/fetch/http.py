"""Fachada de coleta estática — delega para a camada resiliente."""
from __future__ import annotations

from .resilient import obter_binario, obter_html_estatico


def fetch_estatico(url: str) -> str:
    return obter_html_estatico(url)


def fetch_binario(url: str) -> bytes:
    return obter_binario(url)
