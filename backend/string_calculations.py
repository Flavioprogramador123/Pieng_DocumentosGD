"""
Análise de strings CC: em série soma-se tensão (Voc/Vmpp), corrente permanece (Isc/Impp).
Microinversor: 1 módulo por MPPT (strings independentes).
"""

from __future__ import annotations

import math
from typing import Any


def _sf(val, default=0.0) -> float:
    if val in (None, ''):
        return default
    try:
        return float(str(val).replace(',', '.'))
    except (TypeError, ValueError):
        return default


def _si(val, default=0) -> int:
    if val in (None, ''):
        return default
    try:
        return int(float(str(val).replace(',', '.')))
    except (TypeError, ValueError):
        return default


def _detect_inverter_topology(inverter: dict, module_count: int) -> str:
    explicit = (inverter.get('tipo_inversor') or inverter.get('topology') or '').upper()
    if explicit in ('MICRO', 'MICROINVERSOR', 'MICRO-INVERSOR'):
        return 'micro'
    if explicit in ('STRING', 'CENTRAL', 'STRING/MPPT'):
        return 'string'
    power_kw = _sf(inverter.get('potencia', inverter.get('power')))
    qty = max(_si(inverter.get('quantidade', inverter.get('quantity')), 1), 1)
    if power_kw > 0 and power_kw / qty <= 1.5:
        return 'micro'
    if module_count <= qty:
        return 'micro'
    return 'string'


def _modules_per_string(module_count: int, inverter_qty: int, num_mppt: int, topology: str) -> int:
    if topology == 'micro':
        return 1
    mppt_total = max(num_mppt * inverter_qty, 1)
    if module_count <= 0:
        return 0
    return max(1, math.ceil(module_count / mppt_total))


def analyze_dc_strings(modules: list, inverters: list, technical: dict | None = None) -> dict[str, Any]:
    """
    Calcula configuração de strings e correntes CC corretas.
    """
    technical = technical or {}
    messages: list[str] = []

    mod_ref = next((m for m in (modules or []) if _si(m.get('quantity', m.get('quantidade'))) > 0), None)
    if not mod_ref:
        return {'status': 'ERRO', 'messages': ['Informe ao menos um módulo.'], 'strings': []}

    total_modules = sum(_si(m.get('quantity', m.get('quantidade'))) for m in modules or [])
    voc_mod = _sf(mod_ref.get('voc'), 0)
    isc_mod = _sf(mod_ref.get('isc'), 0)
    vmpp_mod = _sf(mod_ref.get('vmpp'), 0)
    impp_mod = _sf(mod_ref.get('impp'), 0)

    if not voc_mod or not isc_mod:
        messages.append('Informe Voc e Isc do módulo para dimensionamento de strings.')

    inv_ref = next((i for i in (inverters or []) if _si(i.get('quantity', i.get('quantity'))) > 0), None)
    if not inv_ref:
        return {'status': 'ERRO', 'messages': ['Informe ao menos um inversor.'], 'strings': []}

    inv_qty = _si(inv_ref.get('quantidade', inv_ref.get('quantity')), 1)
    num_mppt = _si(inv_ref.get('num_mppt'), 0) or _si(technical.get('num_mppt'), 2)
    mppt_min = _sf(inv_ref.get('mppt_min'))
    mppt_max = _sf(inv_ref.get('mppt_max'))

    topology = _detect_inverter_topology(inv_ref, total_modules)
    user_mps = _si(technical.get('modulos_por_string'))
    modules_per_string = user_mps if user_mps > 0 else _modules_per_string(
        total_modules, inv_qty, num_mppt, topology,
    )

    if topology == 'micro':
        strings_count = total_modules
        modules_per_string = 1
        messages.append('Microinversor: 1 módulo por MPPT — tensões individuais, correntes não se somam entre MPPTs.')
    else:
        mppt_total = max(num_mppt * inv_qty, 1)
        strings_count = max(1, math.ceil(total_modules / modules_per_string))
        messages.append(
            f'Inversor string/MPPT: {modules_per_string} módulo(s) em série por string; '
            f'Isc da string = Isc do módulo (corrente NÃO soma em série).'
        )

    string_voc = voc_mod * modules_per_string if voc_mod else 0
    string_vmpp = vmpp_mod * modules_per_string if vmpp_mod else 0
    string_isc = isc_mod  # série: mesma corrente
    string_impp = impp_mod if impp_mod else isc_mod

    # Strings em paralelo no mesmo MPPT (mesma corrente de projeto = Isc × paralelo)
    strings_per_mppt = max(1, math.ceil(strings_count / max(num_mppt * inv_qty, 1)))
    isc_design_a = string_isc * strings_per_mppt * 1.25 if string_isc else 0

    mppt_ok = True
    if mppt_min and string_vmpp and string_vmpp < mppt_min:
        mppt_ok = False
        messages.append(f'Vmpp string ({string_vmpp:.1f} V) abaixo do MPPT mín ({mppt_min} V).')
    if mppt_max and string_voc and string_voc > mppt_max:
        mppt_ok = False
        messages.append(f'Voc string ({string_voc:.1f} V) acima do MPPT máx ({mppt_max} V).')

    status = 'OK'
    if not voc_mod or not isc_mod:
        status = 'ATENÇÃO'
    if not mppt_ok:
        status = 'ATENÇÃO'

    return {
        'status': status,
        'topology': topology,
        'total_modules': total_modules,
        'inverter_quantity': inv_qty,
        'num_mppt_per_inverter': num_mppt,
        'modules_per_string': modules_per_string,
        'strings_count': strings_count,
        'strings_per_mppt': strings_per_mppt,
        'string_voc_v': round(string_voc, 2),
        'string_vmpp_v': round(string_vmpp, 2),
        'string_isc_a': round(string_isc, 2),
        'string_impp_a': round(string_impp, 2),
        'isc_design_a': round(isc_design_a, 2),
        'mppt_ok': mppt_ok,
        'messages': messages,
        'cable_cc_note': (
            f'Bitola CC: dimensionar por Isc de projeto {isc_design_a:.1f} A '
            f'({strings_per_mppt} string(s) em paralelo × Isc {string_isc:.2f} A × 1,25).'
            if isc_design_a else 'Informe Isc para dimensionar cabo CC.'
        ),
    }


def ac_current_a(power_kw: float, voltage_info: dict) -> float:
    """Corrente AC com fator √3 para trifásico (380 V LL em GO)."""
    power_w = power_kw * 1000
    v = voltage_info.get('voltage_v') or 220.0
    if voltage_info.get('system_type') == 'trifasico':
        return power_w / (v * math.sqrt(3)) if v else 0.0
    return power_w / v if v else 0.0
