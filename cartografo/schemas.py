"""Contrato de saída da coleta — independente de fonte/estratégia."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import agora_utc


@dataclass
class DocumentoColetado:
    gestora_slug: str
    titulo: str
    url_documento: str
    texto: str
    tipo: str                                   # "pdf" | "html"
    data_publicacao: Optional[datetime] = None
    coletado_em: datetime = field(default_factory=agora_utc)

    @property
    def hash_conteudo(self) -> str:
        """SHA-256 do texto normalizado — chave de deduplicação."""
        normalizado = re.sub(r"\s+", " ", self.texto).strip().lower()
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return (f"<DocumentoColetado {self.gestora_slug} '{self.titulo[:40]}' "
                f"{len(self.texto)} chars hash={self.hash_conteudo[:10]}>")
