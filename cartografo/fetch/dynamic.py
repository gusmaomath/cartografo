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
        # networkidle nunca dispara em sites com beacons contínuos (Wix etc.);
        # espera o DOM e dá uma janela tolerante para o JS terminar de montar.
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:  # noqa: BLE001 - segue com o que já renderizou
            pass
        if espera_seletor:
            try:
                page.wait_for_selector(espera_seletor, timeout=15_000)
            except Exception:  # noqa: BLE001
                pass
        page.wait_for_timeout(2_000)
        html = page.content()
        browser.close()
        return html
