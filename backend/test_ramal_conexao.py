"""Testes — tabela ramal de conexão Equatorial GO."""

from normas_loader import (
    DEFAULT_CARGA_KW_POR_LIGACAO,
    lookup_ramal_conexao,
    resolve_entrada_uc,
)


def test_ramal_mono_6kw_disjuntor_40():
    faixa = lookup_ramal_conexao('MONOFASICO', 6)
    assert faixa is not None
    assert faixa['disjuntor_A'] == 40
    assert faixa['cabo_cobre_multiplexado_mm2'] == 6


def test_ramal_tri_50kw_disjuntor_100():
    faixa = lookup_ramal_conexao('TRIFASICO', 50)
    assert faixa is not None
    assert faixa['disjuntor_A'] == 100


def test_ramal_tri_30kw_disjuntor_63():
    faixa = lookup_ramal_conexao('TRIFASICO', 30)
    assert faixa['disjuntor_A'] == 63


def test_ramal_bifasico_usa_mono():
    faixa = lookup_ramal_conexao('BIFASICO', 7)
    assert faixa['disjuntor_A'] == 40


def test_resolve_entrada_default_mono_40a():
    entrada = resolve_entrada_uc('GO', 'MONOFASICO', 'RESIDENCIAL')
    assert entrada['disjuntor_a'] == 40


def test_resolve_entrada_tri_50kw():
    entrada = resolve_entrada_uc('GO', 'TRIFASICO', 'RESIDENCIAL', carga_kw=50)
    assert entrada['disjuntor_a'] == 100
    assert '25 mm²' in entrada['bitola_cabo_padrao_mm2']


def test_default_carga_constants():
    assert DEFAULT_CARGA_KW_POR_LIGACAO['MONOFASICO'] == 6
    assert DEFAULT_CARGA_KW_POR_LIGACAO['TRIFASICO'] == 30
