"""Dedup por hash de conteúdo (parte determinística do contrato de coleta)."""
from cartografo.schemas import DocumentoColetado


def _doc(texto: str) -> DocumentoColetado:
    return DocumentoColetado(
        gestora_slug="x", titulo="t", url_documento="u", texto=texto, tipo="html")


def test_hash_ignora_espacos_e_caixa():
    a = _doc("Juros em ALTA  no\tBrasil")
    b = _doc("juros em alta no brasil")
    assert a.hash_conteudo == b.hash_conteudo


def test_hash_distingue_conteudo_diferente():
    assert _doc("long em dólar").hash_conteudo != _doc("short em dólar").hash_conteudo


def test_hash_estavel_e_hex_sha256():
    h = _doc("conteúdo qualquer").hash_conteudo
    assert len(h) == 64 and int(h, 16) >= 0


def test_coletado_em_naive():
    assert _doc("x").coletado_em.tzinfo is None
