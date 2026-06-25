"""Geração do resumo individual de uma carta."""
from __future__ import annotations

import json

from ..config import MAX_CHARS_LLM
from ..registry import REGISTRY
from ..schemas import DocumentoColetado
from .client import LLMClient
from .prompts import SYSTEM_PROMPT_RESUMO


def _truncar(texto: str, limite: int = MAX_CHARS_LLM) -> str:
    """Corta o texto no limite de caracteres, sinalizando o truncamento."""
    if limite <= 0 or len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "\n[…texto truncado por limite de tamanho…]"


def montar_mensagem_usuario(doc: DocumentoColetado) -> str:
    cabecalho = (
        f"GESTORA: {REGISTRY[doc.gestora_slug].nome}\n"
        f"TÍTULO: {doc.titulo}\n"
        f"DATA (inferida): {doc.data_publicacao or 'n/d'}\n"
        f"---- INÍCIO DA CARTA ----\n"
    )
    return cabecalho + _truncar(doc.texto) + "\n---- FIM DA CARTA ----"


def _limpar_cercas(bruto: str) -> str:
    return bruto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def gerar_resumo_individual(doc: DocumentoColetado, llm: LLMClient) -> dict:
    bruto = llm.resumir(SYSTEM_PROMPT_RESUMO, montar_mensagem_usuario(doc))
    return json.loads(_limpar_cercas(bruto))
