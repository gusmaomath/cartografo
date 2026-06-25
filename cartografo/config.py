"""Configuração central. Valores podem ser sobrescritos por variáveis de ambiente."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"


def agora_utc() -> datetime:
    """Timestamp UTC sem tzinfo (naive) — substitui o deprecado datetime.utcnow().

    Mantém os timestamps naive para consistência com as colunas DateTime do
    SQLite, evitando comparar valores aware com os já gravados.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Banco — SQLite apenas (restrição de arquitetura).
DB_PATH = os.getenv("CARTOGRAFO_DB_PATH", str(BASE_DIR / "cartografo.db"))

# HTTP
USER_AGENT = os.getenv(
    "CARTOGRAFO_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
)
HTTP_TIMEOUT = float(os.getenv("CARTOGRAFO_HTTP_TIMEOUT", "30"))
# Atraso educado entre requisições à mesma origem (anti-bloqueio).
DELAY_ENTRE_REQUISICOES = float(os.getenv("CARTOGRAFO_DELAY", "1.5"))

# IA — endpoint do modelo interno do banco (acoplado depois).
MODELO_ENDPOINT = os.getenv("CARTOGRAFO_MODELO_ENDPOINT", "")
MODELO_TOKEN = os.getenv("CARTOGRAFO_MODELO_TOKEN", "")
# Limite defensivo de caracteres do texto da carta enviado ao LLM (evita
# estourar a janela de contexto com PDFs longos). ~0 desliga o corte.
MAX_CHARS_LLM = int(os.getenv("CARTOGRAFO_MAX_CHARS_LLM", "40000"))

# Agendamento (cron). Padrão: toda segunda às 7h.
CRON_DIA_SEMANA = os.getenv("CARTOGRAFO_CRON_DOW", "mon")
CRON_HORA = int(os.getenv("CARTOGRAFO_CRON_HORA", "7"))
