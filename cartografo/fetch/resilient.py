"""Camada de coleta resiliente: retries, rotação de UA e cascata estático↔dinâmico."""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Tuple

import httpx

from ..config import DELAY_ENTRE_REQUISICOES, HTTP_TIMEOUT, USER_AGENT

log = logging.getLogger("cartografo.fetch")

# Rotação de User-Agent: se um for bloqueado, tenta o próximo.
USER_AGENTS = [
    USER_AGENT,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def retry_com_backoff(func: Callable, tentativas: int = 3, base_delay: float = 1.0):
    """Executa func com backoff exponencial + jitter. Relança o último erro."""
    ultimo = None
    for i in range(tentativas):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - resiliência intencional
            ultimo = exc
            if i < tentativas - 1:
                espera = base_delay * (2 ** i) + random.uniform(0, 0.4)
                log.warning("Tentativa %d/%d falhou (%s); aguardando %.1fs",
                            i + 1, tentativas, exc.__class__.__name__, espera)
                time.sleep(espera)
    raise ultimo  # type: ignore[misc]


def _client(ua: str) -> httpx.Client:
    return httpx.Client(
        timeout=HTTP_TIMEOUT, follow_redirects=True,
        headers={"User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9"},
    )


def obter_resposta(url: str) -> httpx.Response:
    """GET resiliente: para cada UA, tenta com retries. Falha só se TODOS falharem."""
    erros: list[str] = []
    for ua in USER_AGENTS:
        def _go(_ua=ua):
            time.sleep(DELAY_ENTRE_REQUISICOES)
            with _client(_ua) as cli:
                r = cli.get(url)
                r.raise_for_status()
                return r
        try:
            return retry_com_backoff(_go, tentativas=2)
        except Exception as exc:  # noqa: BLE001
            erros.append(f"{exc.__class__.__name__}")
    raise RuntimeError(f"Todas as estratégias HTTP falharam para {url}: {erros}")


def obter_html_estatico(url: str) -> str:
    return obter_resposta(url).text


def obter_binario(url: str) -> bytes:
    return obter_resposta(url).content


def obter_html_dinamico(url: str, espera_seletor: str | None = None) -> str:
    from .dynamic import fetch_dinamico
    return fetch_dinamico(url, espera_seletor)


def obter_listagem(url: str, dinamico: bool = False,
                   espera_seletor: str | None = None, min_chars: int = 500) -> Tuple[str, str]:
    """
    Cascata para obter o HTML de uma página:
      - dinamico=True : Playwright  → estático (fallback)
      - dinamico=False: estático    → Playwright (se vier curto/erro)
    Retorna (html, estrategia_usada). Levanta RuntimeError só se tudo falhar.
    """
    if dinamico:
        estrategias = [("dinamico", lambda: obter_html_dinamico(url, espera_seletor)),
                       ("estatico", lambda: obter_html_estatico(url))]
    else:
        estrategias = [("estatico", lambda: obter_html_estatico(url)),
                       ("dinamico", lambda: obter_html_dinamico(url, espera_seletor))]

    ultimo = None
    for nome, fn in estrategias:
        try:
            html = fn()
            if html and len(html) >= min_chars:
                return html, nome
            ultimo = RuntimeError(f"conteúdo curto via {nome} ({len(html or '')} chars)")
            log.warning("Estratégia '%s' devolveu pouco conteúdo para %s", nome, url)
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            log.warning("Estratégia '%s' falhou para %s: %s", nome, url, exc)
    raise RuntimeError(f"Não foi possível obter {url}: {ultimo}")
