"""Descoberta heurística do documento mais recente numa página de listagem."""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..registry import Estrategia, FonteConfig

log = logging.getLogger("cartografo.descoberta")

# Padrões de ano: "2025", "4T25", "1S25", "Mai25", "maio-25", "Set08"…
# O ano de 2 dígitos só vale precedido de trimestre/semestre ou nome de mês —
# senão "Carta-27" viraria 2027.
_RE_ANO4 = re.compile(r"\b(20[0-2]\d)\b")
_RE_ANO2 = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:[1-4]\s?[TtSs]|(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)"
    r"[a-zçã]{0,6}[-_ ]?)"
    r"([0-2]\d)(?!\d)", re.IGNORECASE)

# Sinais textuais de que um link aponta para uma carta/relatório.
PALAVRAS = ["carta", "relatóri", "relatori", "gestor", "mensal", "trimestral",
            "trimestre", "semestre", "semestral",
            "publicac", "insight", "material", "documento", "comentári", "comentari",
            "cenári", "cenari", "análise", "analise", "perspectiv"]
MESES = ["janeiro", "fevereiro", "março", "marco", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
ANOS = ["2024", "2025", "2026", "2027"]
IGNORAR_PREFIXOS = ("#", "mailto:", "tel:", "javascript:")
# Documentos institucionais/regulatórios que NÃO são cartas de gestão.
PALAVRAS_NEGATIVAS = ["privacidade", "privacy", "compliance", "regulament",
                      "codigo-de-etica", "código de ética", "etica", "kyc",
                      "fatca", "pld", "termo de uso", "termos-de-uso",
                      "aviso legal", "aviso-legal", "manual", "formulario",
                      "formulário", "politica", "política", "regimento",
                      "prospecto", "lamina", "lâmina"]


def _eh_pdf(url: str) -> bool:
    u = url.lower()
    return u.endswith(".pdf") or ".pdf?" in u


def _ano_referencia(url: str, texto: str) -> int:
    """Maior ano detectado no link (0 se nenhum) — desempata por recência."""
    alvo = f"{texto} {url}"
    anos = [int(a) for a in _RE_ANO4.findall(alvo)]
    anos += [2000 + int(a) for a in _RE_ANO2.findall(alvo)]
    anos = [a for a in anos if 2005 <= a <= date.today().year + 1]
    return max(anos, default=0)


def _mesmo_dominio(url: str, url_listagem: str) -> bool:
    """Candidato deve estar no domínio da gestora (subdomínios valem)."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    ref = (urlparse(url_listagem).hostname or "").lower().removeprefix("www.")
    return host == ref or host.endswith("." + ref)


def _pontuar(url: str, texto: str, config: FonteConfig, bonus: int) -> int:
    alvo = f"{texto} {url}".lower()
    score = bonus
    if _eh_pdf(url):
        score += 5
    if any(p in alvo for p in PALAVRAS):
        score += 3
    if any(m in alvo for m in MESES):
        score += 2
    if any(a in alvo for a in ANOS):
        score += 2
    prefere_pdf = config.prefere_pdf or config.estrategia == Estrategia.PDF
    if prefere_pdf and not _eh_pdf(url):
        score -= 2
    if any(n in alvo for n in PALAVRAS_NEGATIVAS):
        score -= 8
    # Cartas visivelmente antigas perdem para as recentes mesmo com score maior.
    ano = _ano_referencia(url, texto)
    if 0 < ano < date.today().year - 2:
        score -= 4
    return score


def descobrir_documentos(html: str, config: FonteConfig,
                         limite: int = 10, url_base: str = "") -> list[dict]:
    """
    Retorna até `limite` candidatos [{url, titulo, eh_pdf, score}], do melhor
    para o pior (maior score; empate → posição no documento, topo primeiro).
    Cascata: seletor configurado (bônus alto) → varredura heurística de todos os <a>.
    `url_base` permite resolver links relativos de páginas extras da fonte.
    """
    base = url_base or config.url_listagem
    soup = BeautifulSoup(html, "lxml")
    melhores: dict[str, tuple] = {}  # url -> (score, ano, ordem, titulo)

    # Ordem canônica = posição do link no documento (mais recente costuma estar
    # no topo). Calculada num único scan para que o desempate seja estável
    # independente de qual passada (seletor ou varredura) definiu o score.
    ordem_doc: dict[str, int] = {}
    for i, a in enumerate(soup.find_all("a", href=True)):
        url = urljoin(base, (a.get("href") or "").strip())
        ordem_doc.setdefault(url, i)

    def considerar(anchors, bonus):
        for a in anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(IGNORAR_PREFIXOS):
                continue
            url = urljoin(base, href)
            if urlparse(url).scheme not in ("http", "https"):
                continue
            if not _mesmo_dominio(url, config.url_listagem):
                continue  # agregadores/notícias externas não são a carta
            if url.split("#")[0].rstrip("/") == base.split("#")[0].rstrip("/"):
                continue  # âncora para a própria listagem
            texto = a.get_text(" ", strip=True)
            score = _pontuar(url, texto, config, bonus)
            if score < 3:  # corta ruído de menu/rodapé
                continue
            atual = melhores.get(url)
            if atual is None or score > atual[0]:
                titulo = texto or urlparse(url).path.split("/")[-1]
                melhores[url] = (score, _ano_referencia(url, texto),
                                 ordem_doc.get(url, 10**9), titulo)

    if config.seletor_link:
        considerar(soup.select(config.seletor_link), bonus=8)
    considerar(soup.find_all("a", href=True), bonus=0)

    # maior score → ano mais recente → ordem no documento (topo primeiro)
    ordenados = sorted(melhores.items(),
                       key=lambda kv: (-kv[1][0], -kv[1][1], kv[1][2]))
    return [
        {"url": url, "titulo": titulo, "eh_pdf": _eh_pdf(url), "score": score}
        for url, (score, _ano, _ordem, titulo) in ordenados[:limite]
    ]


def descobrir_documento(html: str, config: FonteConfig) -> Optional[dict]:
    """Melhor candidato único (compatibilidade) — ou None."""
    achados = descobrir_documentos(html, config, limite=1)
    return achados[0] if achados else None
