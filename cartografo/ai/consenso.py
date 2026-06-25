"""Motor de consenso: cruza os resumos estruturados de todas as gestoras."""
from __future__ import annotations

import json
from collections import defaultdict

from .client import LLMClient
from .prompts import SYSTEM_PROMPT_CONSENSO


def agregar_posicoes(resumos: list[dict]) -> dict:
    """
    Pré-agregação DETERMINÍSTICA (auditável): conta long/short por classe de
    ativo a partir dos resumos. Reduz custo e ancora o LLM em fatos.
    """
    tally: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for r in resumos:
        gestora = r.get("gestora", "?")
        for pos in (r.get("posicoes_direcionais") or []):
            classe = (pos.get("ativo_ou_classe") or "").strip().lower()
            direcao = pos.get("direcao") or "neutro"
            if classe:
                tally[classe][direcao].append(gestora)
    return {classe: dict(dirs) for classe, dirs in tally.items()}


def _montar_payload(resumos: list[dict], periodo: str) -> str:
    enxutos = [
        {
            "gestora": r.get("gestora"),
            "posicoes_direcionais": r.get("posicoes_direcionais"),
            "visao_juros": r.get("visao_juros"),
            "visao_inflacao": r.get("visao_inflacao"),
            "teses_setoriais": r.get("teses_setoriais"),
        }
        for r in resumos
    ]
    payload = {
        "periodo": periodo,
        "pre_agregacao_por_classe": agregar_posicoes(resumos),
        "resumos_por_gestora": enxutos,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _limpar_cercas(bruto: str) -> str:
    return bruto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def gerar_relatorio_consenso(resumos: list[dict], periodo: str, llm: LLMClient) -> dict:
    bruto = llm.resumir(SYSTEM_PROMPT_CONSENSO, _montar_payload(resumos, periodo))
    return json.loads(_limpar_cercas(bruto))
