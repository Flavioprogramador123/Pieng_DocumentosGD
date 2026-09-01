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

try:
    from normas_loader import get_uf_voltage_map

    _normas_voltages = get_uf_voltage_map()
    for _uf, _vals in (_normas_voltages or {}).items():
        UF_VOLTAGE.setdefault(_uf, {}).update(_vals)
except Exception:
    pass


def _map_system_type(tipo_ligacao: str | None) -> str:
    t = (tipo_ligacao or '').upper()
    if 'TRIF' in t:
        return 'trifasico'
    if 'BIF' in t:
        return 'bifasico'
    return 'monofasico'


def resolve_ligacao_config(tipo_ligacao: str | None = None) -> dict[str, Any]:
    """
    Mapeia tipo de ligação para NF (fórmula PD), condutores e disjuntor.

    NF em PD = VN × IDG × NF × FP é o número de FASES energizadas (1/2/3),
    não a quantidade de polos do disjuntor nem condutores do ramal.
    Monofásico 220 V: NF=1, 1 condutor fase + 1 neutro, disjuntor monopolar (1 polo no memorial).
    """
    system_type = _map_system_type(tipo_ligacao)
    t = (tipo_ligacao or '').upper()

    if 'TRIF' in t or system_type == 'trifasico':
        return {
            'system_type': 'trifasico',
            'num_fases': 3,
            'qtd_condutores_fase': '3',
            'qtd_condutores_neutro': '1',
            'num_polos_disjuntor': '3',
            'descricao_polos': 'Tripolar',
            'tipo_rede': 'Trifásico',
            'descricao_conexao_inversores': (
                'conectados em fases distintas do sistema trifásico para balanceamento de carga'
            ),
            'descricao_disjuntor_padrao': 'Disjuntor tripolar',
        }
    if 'BIF' in t or system_type == 'bifasico':
        return {
            'system_type': 'bifasico',
            'num_fases': 2,
            'qtd_condutores_fase': '2',
            'qtd_condutores_neutro': '1',
            'num_polos_disjuntor': '3',
            'descricao_polos': 'Tripolar',
            'tipo_rede': 'Bifásico',
            'descricao_conexao_inversores': (
                'conectados em fases distintas do sistema bifásico para balanceamento de carga'
            ),
            'descricao_disjuntor_padrao': 'Disjuntor tripolar',
        }
    return {
        'system_type': 'monofasico',
        'num_fases': 1,
        'qtd_condutores_fase': '1',
        'qtd_condutores_neutro': '1',
        'num_polos_disjuntor': '1',
        'descricao_polos': 'Unipolar',
        'tipo_rede': 'Monofásico',
        'descricao_conexao_inversores': (
            'conectados em paralelo na mesma fase do circuito monofásico'
        ),
        'descricao_disjuntor_padrao': 'Disjuntor monopolar',
    }


def _parse_dual_voltage(text: str | None) -> tuple[float | None, float | None]:
    """Extrai VN (menor) e V_LL (maior) de textos como 127/220V ou 220/380V."""
    if not text:
        return None, None
    nums = [float(n) for n in re.findall(r'\d{2,3}', str(text))]
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        # Valor único (ex.: 220V) = tensão fase-neutro, não linha-linha
        return nums[0], None
    return None, None


def map_inverter_fase(fase_ca: str | None = None) -> str:
    """Fase CA do inversor: monofasico | bifasico | trifasico."""
    t = (fase_ca or '').upper()
    if 'TRIF' in t:
        return 'trifasico'
    if 'BIF' in t:
        return 'bifasico'
    return 'monofasico'


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
    v_ln = v_mono or defaults['monofasico']
    v_ll = v_tri or defaults['trifasico']

    if system_type == 'trifasico':
        voltage = v_ll
        formula = 'Rede concessionária (tensão de atendimento da UC)'
        note = f'Trifásico 120° — VN = {v_ln:.0f} V, V_LL = {v_ll:.0f} V'
    elif system_type == 'bifasico':
        voltage = v_mono or defaults['bifasico']
        v_ln = voltage
        formula = 'I = P / V_fase'
        note = f'Bifásico — V = {voltage:.0f} V'
    else:
        voltage = v_ln
        formula = 'I = P / V'
        note = f'Monofásico — V = {voltage:.0f} V'

    return {
        'system_type': system_type,
        'voltage_v': voltage,
        'voltage_ll_v': v_ll,
        'voltage_ln_v': v_ln,
        'uf': uf_key,
        'formula': formula,
        'note': note,
    }


def normalize_tensao_fase_neutro(
    tensao_atendimento: str | None = None,
    uf: str | None = None,
) -> str:
    """Label F-N para formulário (127V ou 220V). LL vem do tipo de ligação."""
    if tensao_atendimento:
        text = str(tensao_atendimento).upper()
        if '13.8' in text or '13800' in text:
            return '13.8kV'
        nums = [int(n) for n in re.findall(r'\d{2,3}', text)]
        if nums and min(nums) == 127:
            return '127V'
        if nums:
            return '220V'
    uf_key = (uf or 'GO').upper()[:2]
    defaults = UF_VOLTAGE.get(uf_key, UF_VOLTAGE['DEFAULT'])
    return f"{int(defaults['monofasico'])}V"


def suggest_tensao_atendimento(uf: str | None, tipo_ligacao: str | None) -> str:
    """Sugere tensão F-N (127V ou 220V) — trifásico/bifásico fica no tipo de ligação."""
    uf_key = (uf or 'GO').upper()[:2]
    defaults = UF_VOLTAGE.get(uf_key, UF_VOLTAGE['DEFAULT'])
    system_type = _map_system_type(tipo_ligacao)
    if system_type == 'bifasico':
        v = defaults['bifasico']
    else:
        v = defaults['monofasico']
    return f"{int(v)}V"
