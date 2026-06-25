"""Extração de texto de PDF com cascata de extratores: pdfplumber → PyMuPDF → OCR."""
from __future__ import annotations

import io
import logging

log = logging.getLogger("cartografo.extract.pdf")

_MIN_OK = 200  # chars mínimos para considerar a extração bem-sucedida


def _via_pdfplumber(conteudo: bytes) -> str:
    import pdfplumber
    partes = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for page in pdf.pages:
            partes.append(page.extract_text() or "")
    return "\n".join(partes).strip()


def _via_pymupdf(conteudo: bytes) -> str:
    import fitz  # PyMuPDF
    partes = []
    with fitz.open(stream=conteudo, filetype="pdf") as doc:
        for page in doc:
            partes.append(page.get_text() or "")
    return "\n".join(partes).strip()


def _via_ocr(conteudo: bytes) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        log.error("OCR indisponível (instale pytesseract e pdf2image).")
        return ""
    imagens = convert_from_bytes(conteudo, dpi=200)
    return "\n".join(pytesseract.image_to_string(img, lang="por") for img in imagens)


def extrair_texto_pdf(conteudo: bytes) -> str:
    """Tenta extratores em ordem; OCR é o último recurso. Mantém o melhor resultado."""
    melhor = ""
    for nome, fn in (("pdfplumber", _via_pdfplumber), ("pymupdf", _via_pymupdf)):
        try:
            texto = fn(conteudo)
        except ImportError:
            log.info("Extrator '%s' não instalado; pulando.", nome)
            continue
        except Exception as exc:  # noqa: BLE001
            log.warning("Extrator '%s' falhou: %s", nome, exc)
            continue
        if len(texto) > len(melhor):
            melhor = texto
        if len(melhor) >= _MIN_OK:
            return melhor

    if len(melhor) < _MIN_OK:  # provável PDF escaneado
        log.warning("Texto insuficiente (%d chars); tentando OCR.", len(melhor))
        ocr = _via_ocr(conteudo)
        if len(ocr) > len(melhor):
            melhor = ocr
    return melhor
