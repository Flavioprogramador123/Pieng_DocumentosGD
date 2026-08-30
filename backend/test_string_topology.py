"""Testes de topologia MPPT / strings — casos em docs/exemplos_interacao_modulo_inversor.json"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from string_calculations import (
    _detect_inverter_topology,
    analyze_dc_strings,
    label_tipo_equipamento_inversor,
)
from string_topology import suggest_string_layout

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / 'docs' / 'exemplos_interacao_modulo_inversor.json'


def _load_cases():
    data = json.loads(EXAMPLES.read_text(encoding='utf-8'))
    return data.get('casos') or []


def _inverter_from_case(inv: dict) -> dict:
    icc = inv.get('icc_mppt')
    icc_json = json.dumps([icc] * inv.get('mppt', 1)) if isinstance(icc, (int, float)) else None
    strings = inv.get('strings_por_mppt')
    strings_json = json.dumps(strings) if isinstance(strings, list) else None
    tipo = (inv.get('tipo') or '').upper()
    return {
        'model': inv.get('modelo'),
        'potencia_kw': inv.get('kw'),
        'num_mppt': inv.get('mppt'),
        'mppt_min': 90,
        'mppt_max': 550,
        'tensao_max_cc': 600,
        'strings_por_mppt_json': strings_json,
        'icc_mppt_json': icc_json,
        'tipo_inversor': 'MICRO' if tipo == 'MICRO' else 'STRING',
        'quantidade': 1,
    }


def _module_from_case(mod: dict) -> dict:
    return {
        'voc': mod.get('voc', 41.7),
        'isc': mod.get('isc', 15.84),
        'vmpp': mod.get('vmpp', 34.8),
        'impp': mod.get('impp', mod.get('isc', 15.84)),
        'quantidade': 1,
    }


@pytest.mark.parametrize('case', _load_cases(), ids=lambda c: c.get('id', '?'))
def test_exemplos_interacao(case):
    projeto = case['projeto']
    qtd = projeto['qtd_modulos']
    inv_qty = projeto.get('qtd_inversores', 1)

    module = _module_from_case(case['modulo'])
    module['quantidade'] = qtd
    inverter = _inverter_from_case(case['inversor'])
    inverter['quantidade'] = inv_qty

    expected = case['config_esperada']
    validacao = case.get('validacao') or {}
    topology = 'micro' if case['inversor'].get('tipo') == 'micro' else 'string'

    layout = suggest_string_layout(
        qtd,
        inverter,
        module,
        inverter_qty=inv_qty,
        topology=topology,
    )

    assert layout['modules_per_string'] == expected['modulos_por_string']
    assert layout['strings_count'] == expected['strings_total']
    if 'strings_por_mppt' in expected and validacao.get('icc_ok') is not False:
        assert layout['strings_per_mppt'] == expected['strings_por_mppt']
    if 'mppt_usados' in expected:
        assert layout['mppt_used'] == expected['mppt_usados']

    result = analyze_dc_strings([module], [inverter], {})
    assert result['modules_per_string'] == expected['modulos_por_string']
    assert result['strings_count'] == expected['strings_total']

    if 'icc_ok' in validacao:
        if validacao['icc_ok'] is False and result.get('icc_ok'):
            assert result['strings_per_mppt'] < expected.get('strings_por_mppt', result['strings_per_mppt'])
        else:
            assert result.get('icc_ok') is validacao['icc_ok']
    if validacao.get('vmpp_string_v'):
        assert abs(result['string_vmpp_v'] - validacao['vmpp_string_v']) < 1.0


def test_risen600_icc_excede_saj_3k():
    """Isc 18,26 A > Icc 16 A — deve sinalizar ATENÇÃO."""
    module = {'voc': 41.7, 'isc': 18.26, 'vmpp': 34.8, 'impp': 17.25, 'quantidade': 8}
    inverter = {
        'model': 'R6-3K-S3',
        'potencia_kw': 3,
        'num_mppt': 3,
        'mppt_min': 90,
        'mppt_max': 550,
        'tensao_max_cc': 600,
        'strings_por_mppt_json': '[1,1,1]',
        'icc_mppt_json': '[16,16,16]',
        'quantidade': 1,
    }
    result = analyze_dc_strings([module], [inverter], {})
    assert result['modules_per_string'] == 8
    assert result['strings_count'] == 1
    assert result['icc_ok'] is False
    assert result['status'] == 'ATENÇÃO'


def test_saj_25kw_nao_e_micro():
    """2× SAJ 25 kW + 50 módulos — inversor string, não micro-inversor."""
    module = {'voc': 41.7, 'isc': 15.84, 'vmpp': 34.8, 'impp': 15.5, 'quantidade': 50}
    inverter = {
        'fabricante': 'SAJ',
        'model': 'INVERSOR SAJ 25KW TRIFÁSICO 220V',
        'potencia': 25,
        'quantidade': 2,
        'num_mppt': 2,
        'mppt_min': 180,
        'mppt_max': 1000,
        'tipo_inversor': 'STRING',
    }
    topo = _detect_inverter_topology(inverter, 50, {'tipo_inversor': 'STRING'})
    assert topo == 'string'
    assert label_tipo_equipamento_inversor('STRING', topo, 25) == 'Inversor'
    result = analyze_dc_strings([module], [inverter], {'tipo_inversor': 'STRING'})
    assert result['topology'] == 'string'


def test_label_tipo_equipamento_inversor():
    assert label_tipo_equipamento_inversor('MICRO', 'micro', 1) == 'Micro-inversor'
    assert label_tipo_equipamento_inversor('STRING', 'string', 8) == 'Inversor'
    assert label_tipo_equipamento_inversor(None, None, 8) == 'Inversor'
    assert label_tipo_equipamento_inversor(None, 'micro', 1) == 'Micro-inversor'
    assert label_tipo_equipamento_inversor('STRING', 'string', 25) == 'Inversor'
