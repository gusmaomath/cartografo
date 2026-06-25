"""Pré-agregação determinística e limpeza de cercas markdown."""
from cartografo.ai.consenso import _limpar_cercas, agregar_posicoes


def test_agregar_conta_long_short_por_classe():
    resumos = [
        {"gestora": "A", "posicoes_direcionais": [
            {"ativo_ou_classe": "Bolsa BR", "direcao": "long"}]},
        {"gestora": "B", "posicoes_direcionais": [
            {"ativo_ou_classe": "bolsa br", "direcao": "long"}]},
        {"gestora": "C", "posicoes_direcionais": [
            {"ativo_ou_classe": "Bolsa BR", "direcao": "short"}]},
    ]
    tally = agregar_posicoes(resumos)
    assert tally["bolsa br"]["long"] == ["A", "B"]
    assert tally["bolsa br"]["short"] == ["C"]


def test_agregar_ignora_classe_vazia_e_lista_ausente():
    resumos = [
        {"gestora": "A", "posicoes_direcionais": [{"ativo_ou_classe": "", "direcao": "long"}]},
        {"gestora": "B"},  # sem posicoes_direcionais
    ]
    assert agregar_posicoes(resumos) == {}


def test_limpar_cercas_remove_bloco_json():
    assert _limpar_cercas('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _limpar_cercas('```\n{"a": 1}\n```') == '{"a": 1}'
    assert _limpar_cercas('{"a": 1}') == '{"a": 1}'
