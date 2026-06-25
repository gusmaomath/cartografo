"""Orquestração resiliente: coleta -> persistência -> resumo -> consenso."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from .config import agora_utc
from .ai.client import LLMClient, PipelineIANaoAcoplado
from .ai.consenso import gerar_relatorio_consenso
from .ai.resumo import gerar_resumo_individual
from .db.repository import (documentos_sem_resumo, get_engine, init_db,
                            listar_resumos, registrar_log_coleta,
                            salvar_consenso, salvar_documento, salvar_resumo)
from .fetch.resilient import retry_com_backoff
from .registry import REGISTRY
from .schemas import DocumentoColetado
from .scrapers.factory import get_scraper

log = logging.getLogger("cartografo.pipeline")


def _coletar_uma(slug: str) -> Optional[DocumentoColetado]:
    """Coleta com retry. Cada fonte é isolada — exceções não vazam para o lote."""
    return retry_com_backoff(
        lambda: get_scraper(slug).coletar_mais_recente(),
        tentativas=2, base_delay=2.0,
    )


def executar_coleta(slugs: Optional[list[str]] = None) -> dict:
    """
    Tenta coletar a carta mais recente de TODAS as fontes ativas (não só as
    com scraper dedicado). Registra sucesso/falha por fonte e segue em frente.
    Retorna um resumo agregado da execução.
    """
    engine = get_engine()
    init_db(engine)
    alvos = slugs or [s for s, c in REGISTRY.items() if c.ativo]

    novos_ids: list[int] = []
    detalhes: list[dict] = []
    sucessos = falhas = duplicados = 0

    for slug in alvos:
        nome = REGISTRY[slug].nome
        log.info("--- Coletando: %s (%s) ---", nome, slug)
        try:
            doc = _coletar_uma(slug)
        except Exception as exc:  # noqa: BLE001 - resiliência por fonte
            falhas += 1
            motivo = f"{exc.__class__.__name__}: {exc}"[:380]
            log.warning("Falha em %s: %s", slug, motivo)
            with Session(engine) as s:
                registrar_log_coleta(s, slug, sucesso=False, motivo=motivo)
            detalhes.append({"gestora": slug, "ok": False, "motivo": motivo})
            continue

        if not doc or len(doc.texto) < 120:
            falhas += 1
            motivo = "documento vazio ou texto insuficiente"
            with Session(engine) as s:
                registrar_log_coleta(s, slug, sucesso=False, motivo=motivo)
            detalhes.append({"gestora": slug, "ok": False, "motivo": motivo})
            continue

        with Session(engine) as s:
            registro = salvar_documento(s, doc)
            if registro is None:
                duplicados += 1
                registrar_log_coleta(s, slug, sucesso=True, motivo="duplicado (já coletado)")
                detalhes.append({"gestora": slug, "ok": True, "motivo": "duplicado"})
                continue
            novos_ids.append(registro.id)
            sucessos += 1
            registrar_log_coleta(s, slug, sucesso=True, documento_id=registro.id)
            detalhes.append({"gestora": slug, "ok": True, "documento_id": registro.id})

    resumo = {"total": len(alvos), "novos": sucessos, "duplicados": duplicados,
              "falhas": falhas, "novos_ids": novos_ids, "detalhes": detalhes}
    log.info("Coleta concluída: %d novos, %d duplicados, %d falhas (de %d fontes).",
             sucessos, duplicados, falhas, len(alvos))
    return resumo


def executar_resumos(llm: Optional[LLMClient] = None) -> int:
    """Gera resumo para cada documento ainda sem resumo. No-op se IA não acoplada."""
    llm = llm or PipelineIANaoAcoplado()
    engine = get_engine()
    feitos = 0
    with Session(engine) as s:
        for doc in documentos_sem_resumo(s):
            coletado = DocumentoColetado(
                gestora_slug=doc.gestora_slug, titulo=doc.titulo,
                url_documento=doc.url_documento, texto=doc.texto, tipo=doc.tipo,
                data_publicacao=doc.data_publicacao)
            try:
                resumo = gerar_resumo_individual(coletado, llm)
            except NotImplementedError as exc:
                log.info("IA não acoplada: %s", exc)
                break
            except Exception:  # noqa: BLE001
                log.exception("Falha ao resumir documento id=%s", doc.id)
                continue
            salvar_resumo(s, doc.id, resumo)
            feitos += 1
    log.info("Resumos gerados: %d", feitos)
    return feitos


def executar_consenso(periodo: Optional[str] = None, llm: Optional[LLMClient] = None) -> Optional[int]:
    llm = llm or PipelineIANaoAcoplado()
    periodo = periodo or agora_utc().strftime("%m/%Y")
    engine = get_engine()
    with Session(engine) as s:
        resumos_orm = listar_resumos(s)
        if not resumos_orm:
            log.warning("Sem resumos para gerar consenso.")
            return None
        resumos = [r.json_completo for r in resumos_orm]
        ids = [r.documento_id for r in resumos_orm]
        try:
            relatorio = gerar_relatorio_consenso(resumos, periodo, llm)
        except NotImplementedError as exc:
            log.info("IA não acoplada: %s", exc)
            return None
        reg = salvar_consenso(s, periodo, relatorio.get("consensos", []),
                              relatorio.get("divergencias", []), ids,
                              leitura_macro=relatorio.get("leitura_macro"))
        log.info("Consenso gravado id=%s", reg.id)
        return reg.id


def executar_ciclo_completo(llm: Optional[LLMClient] = None) -> None:
    executar_coleta()
    executar_resumos(llm)
    executar_consenso(llm=llm)
