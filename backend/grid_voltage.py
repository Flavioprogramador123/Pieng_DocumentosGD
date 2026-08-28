"""
Tensões de atendimento por UF e tipo de ligação (linha-neutro / linha-linha).
Goiás: 220 V monofásico, 380 V trifásico (linha-linha, defasagem 120°).
"""

from __future__ import annotations

import re
from typing import Any

# Tensão de cálculo para corrente AC (V)
# monofasico/bifasico: linha-neutro (ou fase-neutro)
# trifasico: linha-linha (√3 entra na fórmula P = √3 · V_LL · I)
UF_VOLTAGE: dict[str, dict[str, float]] = {
    'GO': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'MA': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'PI': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'PA': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'SP': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'RJ': {'monofasico': 127.0, 'bifasico': 220.0, 'trifasico': 380.0},
    'DEFAULT': {'monofasico': 220.0, 'bifasico': 220.0, 'trifasico': 380.0},
}


def _map_system_type(tipo_ligacao: str | None) -> str:
    t = (tipo_ligacao or '').upper()
    if 'TRIF' in t:
        return 'trifasico'
    if 'BIF' in t:
        return 'bifasico'
    return 'monofasico'


def _parse_dual_voltage(text: str | None) -> tuple[float | None, float | None]:
    """Extrai par mono/bi e trifásico de textos como 127/220V ou 220/380V."""
    if not text:
        return None, None
    nums = [float(n) for n in re.findall(r'\d{2,3}', str(text))]
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def resolve_ac_voltage(
    uf: str | None = None,
    tipo_ligacao: str | None = None,
    tensao_atendimento: str | None = None,
) -> dict[str, Any]:
    """
    Retorna tensão de cálculo, tipo de sistema e notas para memorial/cálculos.
    Trifásico usa V_LL (ex.: 380 V em GO); corrente: I = P / (√3 · V_LL).
    """
    system_type = _map_system_type(tipo_ligacao)
    uf_key = (uf or '').upper()[:2] or 'DEFAULT'
    defaults = UF_VOLTAGE.get(uf_key, UF_VOLTAGE['DEFAULT'])

    v_mono, v_tri = _parse_dual_voltage(tensao_atendimento)
    if system_type == 'trifasico':
        voltage = v_tri or defaults['trifasico']
        formula = 'I = P / (√3 × V_LL)'
        note = f'Trifásico 120° — V_LL = {voltage:.0f} V'
    elif system_type == 'bifasico':
        voltage = v_mono or defaults['bifasico']
        formula = 'I = P / V_fase'
        note = f'Bifásico — V = {voltage:.0f} V'
    else:
        voltage = v_mono or defaults['monofasico']
        formula = 'I = P / V'
        note = f'Monofásico — V = {voltage:.0f} V'

    return {
        'system_type': system_type,
        'voltage_v': voltage,
        'voltage_ll_v': v_tri or defaults['trifasico'],
        'voltage_ln_v': v_mono or defaults['monofasico'],
        'uf': uf_key,
        'formula': formula,
        'note': note,
    }


def suggest_tensao_atendimento(uf: str | None, tipo_ligacao: str | None) -> str:
    """Sugere label para o formulário (ex.: 220V ou 220/380V)."""
    uf_key = (uf or 'GO').upper()[:2]
    defaults = UF_VOLTAGE.get(uf_key, UF_VOLTAGE['DEFAULT'])
    system_type = _map_system_type(tipo_ligacao)
    if system_type == 'trifasico':
        return f"{int(defaults['monofasico'])}/{int(defaults['trifasico'])}V"
    return f"{int(defaults['monofasico'])}V"
