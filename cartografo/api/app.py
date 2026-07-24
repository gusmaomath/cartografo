"""API FastAPI + servidor do painel vanilla JS."""
from __future__ import annotations

import logging
import threading

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from ..config import WEB_DIR, agora_utc
from ..db.models import Documento
from ..db.repository import (get_engine, init_db, listar_documentos,
                             listar_resumos, status_por_gestora, ultimo_consenso)
from ..pipeline import executar_coleta

log = logging.getLogger("cartografo.api")

app = FastAPI(title="Cartógrafo — Cartas de Gestores", version="0.1.0")
_engine = get_engine()
init_db(_engine)

# Estado da coleta em background (uma por vez; protegido por lock).
_lock_coleta = threading.Lock()
_estado_coleta: dict = {"rodando": False, "iniciada_em": None, "concluida_em": None,
                        "resultado": None, "erro": None}


def _rodar_coleta() -> None:
    try:
        resultado = executar_coleta()
        _estado_coleta["resultado"] = resultado
        _estado_coleta["erro"] = None
    except Exception as exc:  # noqa: BLE001 - reportado via /api/coletar/status
        log.exception("Coleta em background falhou")
        _estado_coleta["erro"] = f"{exc.__class__.__name__}: {exc}"
    finally:
        _estado_coleta["rodando"] = False
        _estado_coleta["concluida_em"] = agora_utc().isoformat()
        _lock_coleta.release()


@app.get("/api/documentos")
def get_documentos():
    with Session(_engine) as s:
        return [
            {"id": d.id, "gestora": d.gestora_slug, "titulo": d.titulo,
             "tipo": d.tipo, "status": d.status,
             "data_publicacao": d.data_publicacao.isoformat() if d.data_publicacao else None,
             "coletado_em": d.coletado_em.isoformat(), "url": d.url_documento}
            for d in listar_documentos(s)
        ]


@app.get("/api/documentos/{doc_id}")
def get_documento(doc_id: int):
    with Session(_engine) as s:
        d = s.get(Documento, doc_id)
        if not d:
            raise HTTPException(404, "Documento não encontrado")
        return {"id": d.id, "gestora": d.gestora_slug, "titulo": d.titulo,
                "tipo": d.tipo, "texto": d.texto, "url": d.url_documento}


# Cache do documento original (evita rebaixar o PDF a cada visualização).
_cache_original: dict[int, tuple[str, bytes]] = {}
_CACHE_ORIGINAL_MAX = 20


@app.get("/api/documentos/{doc_id}/original")
def get_documento_original(doc_id: int):
    """Serve o documento original (PDF/HTML) via proxy same-origin.

    Permite embutir o PDF no painel com tabelas/gráficos preservados —
    iframes diretos para o domínio da gestora esbarram em CORS/X-Frame-Options.
    """
    with Session(_engine) as s:
        d = s.get(Documento, doc_id)
        if not d:
            raise HTTPException(404, "Documento não encontrado")
        url = d.url_documento
    if doc_id not in _cache_original:
        from ..fetch.resilient import obter_resposta
        try:
            r = obter_resposta(url)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Falha ao baixar o original: {exc}") from exc
        ctype = r.headers.get("content-type", "application/octet-stream").split(";")[0]
        if r.content[:4] == b"%PDF":
            ctype = "application/pdf"
        while len(_cache_original) >= _CACHE_ORIGINAL_MAX:
            _cache_original.pop(next(iter(_cache_original)))
        _cache_original[doc_id] = (ctype, r.content)
    ctype, conteudo = _cache_original[doc_id]
    return Response(content=conteudo, media_type=ctype,
                    headers={"Content-Disposition": "inline"})


@app.get("/api/resumos")
def get_resumos():
    with Session(_engine) as s:
        return [
            {"documento_id": r.documento_id, "tese_principal": r.tese_principal,
             "visao_juros": r.visao_juros, "visao_inflacao": r.visao_inflacao,
             "posicoes_direcionais": r.posicoes_direcionais,
             "teses_setoriais": r.teses_setoriais, "completo": r.json_completo}
            for r in listar_resumos(s)
        ]


@app.get("/api/consenso")
def get_consenso():
    with Session(_engine) as s:
        c = ultimo_consenso(s)
        if not c:
            return {"periodo": None, "consensos": [], "divergencias": [], "leitura_macro": None}
        return {"periodo": c.periodo, "consensos": c.consensos,
                "divergencias": c.divergencias, "leitura_macro": c.leitura_macro,
                "criado_em": c.criado_em.isoformat()}


@app.post("/api/coletar", status_code=202)
def post_coletar(tarefas: BackgroundTasks):
    """Dispara a coleta em background. Não bloqueia o request (pode levar minutos).

    Acompanhe o andamento em GET /api/coletar/status. Recusa um novo disparo
    enquanto outra coleta estiver em andamento.
    """
    if not _lock_coleta.acquire(blocking=False):
        raise HTTPException(409, "Já existe uma coleta em andamento.")
    _estado_coleta.update(rodando=True, iniciada_em=agora_utc().isoformat(),
                          concluida_em=None, resultado=None, erro=None)
    tarefas.add_task(_rodar_coleta)
    return {"status": "iniciada", "iniciada_em": _estado_coleta["iniciada_em"]}


@app.get("/api/coletar/status")
def get_coletar_status():
    """Estado da última/atual coleta disparada via API."""
    return _estado_coleta


@app.get("/api/status-fontes")
def get_status_fontes():
    """Último resultado de coleta por gestora (sucesso/falha)."""
    with Session(_engine) as s:
        return status_por_gestora(s)


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")
