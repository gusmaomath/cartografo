"""Coleta dinâmica via Playwright (SPAs/JS). Import preguiçoso."""
from __future__ import annotations

from typing import Optional

from ..config import USER_AGENT


def fetch_dinamico(url: str, espera_seletor: Optional[str] = None) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Rode: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="networkidle", timeout=60_000)
        if espera_seletor:
            page.wait_for_selector(espera_seletor, timeout=15_000)
        html = page.content()
        browser.close()
        return html
