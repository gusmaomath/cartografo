"""Acesso a dados: engine, init e operações de gravação/leitura."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from ..config import DB_PATH
from ..registry import REGISTRY
from ..schemas import DocumentoColetado
from .models import (Base, Documento, Gestora, LogColeta, RelatorioConsenso,
                     ResumoIndividual)

log = logging.getLogger("cartografo.db")


@lru_cache(maxsize=None)
def get_engine(caminho: str = DB_PATH):
    """Engine SQLite cacheada por caminho (evita recriar a cada chamada)."""
    engine = create_engine(f"sqlite:///{caminho}", future=True)

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for slug, cfg in REGISTRY.items():
            if s.get(Gestora, slug) is None:
                s.add(Gestora(slug=slug, nome=cfg.nome))
        s.commit()


def salvar_documento(session: Session, doc: DocumentoColetado) -> Optional[Documento]:
    """Persiste o documento. Retorna None se duplicado (mesmo hash)."""
    if session.scalar(select(Documento).where(Documento.hash_conteudo == doc.hash_conteudo)):
        log.info("Duplicado, pulando: %s", doc.titulo[:50])
        return None
    registro = Documento(
        gestora_slug=doc.gestora_slug, titulo=doc.titulo, url_documento=doc.url_documento,
        tipo=doc.tipo, data_publicacao=doc.data_publicacao,
        hash_conteudo=doc.hash_conteudo, texto=doc.texto,
    )
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def salvar_resumo(session: Session, documento_id: int, resumo: dict) -> ResumoIndividual:
    registro = ResumoIndividual(
        documento_id=documento_id,
        tese_principal=resumo.get("tese_principal"),
        visao_juros=resumo.get("visao_juros"),
        visao_inflacao=resumo.get("visao_inflacao"),
        posicoes_direcionais=resumo.get("posicoes_direcionais"),
        teses_setoriais=resumo.get("teses_setoriais"),
        json_completo=resumo,
    )
    session.add(registro)
    doc = session.get(Documento, documento_id)
    if doc:
        doc.status = "resumido"
    session.commit()
    session.refresh(registro)
    return registro


def salvar_consenso(session: Session, periodo: str, consensos: list,
                    divergencias: list, documentos_incluidos: list,
                    leitura_macro: Optional[str] = None) -> RelatorioConsenso:
    registro = RelatorioConsenso(
        periodo=periodo, consensos=consensos, divergencias=divergencias,
        leitura_macro=leitura_macro, documentos_incluidos=documentos_incluidos,
    )
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


# ----- Leituras (usadas pela API) -----
def listar_documentos(session: Session) -> list[Documento]:
    return list(session.scalars(select(Documento).order_by(Documento.coletado_em.desc())))


def documentos_sem_resumo(session: Session) -> list[Documento]:
    return list(session.scalars(select(Documento).where(Documento.status == "coletado")))


def listar_resumos(session: Session) -> list[ResumoIndividual]:
    return list(session.scalars(select(ResumoIndividual).order_by(ResumoIndividual.criado_em.desc())))


def ultimo_consenso(session: Session) -> Optional[RelatorioConsenso]:
    return session.scalar(select(RelatorioConsenso).order_by(RelatorioConsenso.criado_em.desc()))


def registrar_log_coleta(session: Session, gestora_slug: str, sucesso: bool,
                         documento_id: Optional[int] = None,
                         motivo: Optional[str] = None) -> None:
    session.add(LogColeta(gestora_slug=gestora_slug, sucesso=sucesso,
                          documento_id=documento_id, motivo=motivo))
    session.commit()


def ultimos_logs(session: Session, limite: int = 50) -> list[LogColeta]:
    return list(session.scalars(
        select(LogColeta).order_by(LogColeta.executado_em.desc()).limit(limite)))


def status_por_gestora(session: Session) -> list[dict]:
    """Último resultado de coleta de cada gestora (para o painel)."""
    vistos: dict[str, dict] = {}
    for lg in ultimos_logs(session, limite=500):
        if lg.gestora_slug not in vistos:
            vistos[lg.gestora_slug] = {
                "gestora": lg.gestora_slug, "sucesso": lg.sucesso,
                "motivo": lg.motivo, "em": lg.executado_em.isoformat()}
    return list(vistos.values())
