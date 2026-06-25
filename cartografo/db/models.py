"""Modelos ORM (SQLAlchemy) — SQLite."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (DateTime, ForeignKey, JSON, String, Text, UniqueConstraint)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column, relationship)

from ..config import agora_utc


class Base(DeclarativeBase):
    pass


class Gestora(Base):
    __tablename__ = "gestoras"
    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    documentos: Mapped[list["Documento"]] = relationship(back_populates="gestora")


class Documento(Base):
    __tablename__ = "documentos"
    __table_args__ = (UniqueConstraint("hash_conteudo", name="uq_doc_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gestora_slug: Mapped[str] = mapped_column(ForeignKey("gestoras.slug"))
    titulo: Mapped[str] = mapped_column(String(300))
    url_documento: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(10))
    data_publicacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hash_conteudo: Mapped[str] = mapped_column(String(64), index=True)
    texto: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="coletado")
    coletado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    gestora: Mapped["Gestora"] = relationship(back_populates="documentos")
    resumo: Mapped[Optional["ResumoIndividual"]] = relationship(
        back_populates="documento", uselist=False)


class ResumoIndividual(Base):
    __tablename__ = "resumos_individuais"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id"), unique=True)
    tese_principal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visao_juros: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    visao_inflacao: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    posicoes_direcionais: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    teses_setoriais: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    json_completo: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    documento: Mapped["Documento"] = relationship(back_populates="resumo")


class RelatorioConsenso(Base):
    __tablename__ = "relatorios_consenso"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    periodo: Mapped[str] = mapped_column(String(40))
    consensos: Mapped[list] = mapped_column(JSON)
    divergencias: Mapped[list] = mapped_column(JSON)
    leitura_macro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documentos_incluidos: Mapped[list] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)


class LogColeta(Base):
    """Registro de cada tentativa de coleta — observabilidade de falhas/fallbacks."""
    __tablename__ = "logs_coleta"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gestora_slug: Mapped[str] = mapped_column(String(40), index=True)
    sucesso: Mapped[bool] = mapped_column(default=False)
    documento_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    motivo: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    executado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
