"""
QDCA — quadro de distribuição CA da usina solar (editável pelo usuário).

Micro: distribuição por fase (A/B/C) + disjuntor por ramal + DPS.
String: disjuntor(ões) CA do(s) inversor(es).
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from nbr5410_calculations import distribute_micros_across_phases, standard_breaker_rating

MAX_MICROS_POR_DISJUNTOR = 3
MAX_KW_POR_FASE_DEFAULT = 7.5
AMPACITY_MM2_A: dict[str, int] = {'4': 35, '6': 45, '10': 55, '16': 70}


def _bitola_mm2(val: str | None, default: str = '6') -> str:
    text = str(val or default).strip()
    digits = ''.join(c for c in text if c.isdigit())
    return digits or default


def _i_max_segment(*, disj_a: int, bitola: str) -> int:
    return min(disj_a, AMPACITY_MM2_A.get(_bitola_mm2(bitola), 45))


def pack_micro_breaker_rows(
    num_micros: int,
    *,
    power_per_micro_kw: float = 2.25,
    network_type: str = 'trifasico',
    micros_per_breaker: int = MAX_MICROS_POR_DISJUNTOR,
    max_kw_per_phase: float = MAX_KW_POR_FASE_DEFAULT,
    manual_per_phase: list[int] | None = None,
    mode: str = 'economia',
    voltage_ln_v: float = 220.0,
) -> list[dict[str, Any]]:
    """Uma linha por disjuntor QDCA (até 3 micros). Modo economia concentra na mesma fase."""
    labels = phase_labels_for_network(network_type)
    per_breaker = max(1, min(MAX_MICROS_POR_DISJUNTOR, int(micros_per_breaker or 3)))

    if manual_per_phase and sum(manual_per_phase) == num_micros:
        phase_queues: list[tuple[str, int]] = []
        for label, count in zip(labels, manual_per_phase):
            rem = int(count)
            while rem > 0:
                chunk = min(per_breaker, rem)
                phase_queues.append((label, chunk))
                rem -= chunk
    elif mode == 'balanceamento' and network_type == 'trifasico' and len(labels) == 3:
        dist = distribute_micros_across_phases(num_micros, 3)
        phase_queues = []
        for label, count in zip(labels, dist):
            rem = count
            while rem > 0:
                chunk = min(per_breaker, rem)
                phase_queues.append((label, chunk))
                rem -= chunk
    else:
        phase_queues = []
        remaining = num_micros
        phase_idx = 0
        phase_kw: dict[str, float] = {lb: 0.0 for lb in labels}
        while remaining > 0:
            fase = labels[min(phase_idx, len(labels) - 1)]
            chunk = min(per_breaker, remaining)
            if phase_kw[fase] > 0 and phase_kw[fase] + chunk * power_per_micro_kw > max_kw_per_phase:
                phase_idx += 1
                if phase_idx < len(labels):
                    fase = labels[phase_idx]
                    chunk = min(per_breaker, remaining)
                else:
                    fase = labels[-1]
            if phase_kw[fase] + chunk * power_per_micro_kw > max_kw_per_phase and phase_kw[fase] > 0:
                chunk = max(1, int((max_kw_per_phase - phase_kw[fase]) / power_per_micro_kw))
                chunk = min(chunk, per_breaker, remaining)
            phase_queues.append((fase, chunk))
            phase_kw[fase] += chunk * power_per_micro_kw
            remaining -= chunk

    i_micro = power_per_micro_kw * 1000 / voltage_ln_v if voltage_ln_v else 0.0
    rows: list[dict[str, Any]] = []
    for fase, micros in phase_queues:
        i_nom = round(i_micro * micros, 2)
        i_des = round(i_nom * 1.25, 2)
        br = standard_breaker_rating(i_des)
        bitola = '6'
        rows.append({
            'fase': fase,
            'micros': micros,
            'current_a': i_nom,
            'current_design_a': i_des,
            'breaker_a': br,
            'bitola_ca': bitola,
            'i_max_a': _i_max_segment(disj_a=br, bitola=bitola),
            'equipamento': f'{micros} micro(s) — Fase {fase}',
        })
    return rows


def network_type_from_ligacao(tipo_ligacao: str | None) -> str:
    t = (tipo_ligacao or 'MONOFASICO').upper()
    if 'TRIF' in t:
        return 'trifasico'
    if 'BIF' in t:
        return 'bifasico'
    return 'monofasico'


def phase_labels_for_network(network_type: str) -> list[str]:
    if network_type == 'trifasico':
        return ['A', 'B', 'C']
    if network_type == 'bifasico':
        return ['A', 'B']
    return ['A']


def _safe_int(val, default: int = 0) -> int:
    if val in (None, ''):
        return default
    try:
        return int(float(str(val).replace(',', '.')))
    except (TypeError, ValueError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    if val in (None, ''):
        return default
    try:
        return float(str(val).replace(',', '.'))
    except (TypeError, ValueError):
        return default


def parse_user_micros_per_phase(
    technical: dict[str, Any] | None,
    *,
    num_micros: int,
    network_type: str,
) -> tuple[list[int], bool]:
    """
    Lê qdca_micros_fase_a/b/c do formulário.
    Retorna (contagens por fase, foi_manual).
    """
    technical = technical or {}
    labels = phase_labels_for_network(network_type)
    field_by_label = {
        'A': 'qdca_micros_fase_a',
        'B': 'qdca_micros_fase_b',
        'C': 'qdca_micros_fase_c',
    }
    raw: list[int | None] = []
    any_set = False
    for label in labels:
        key = field_by_label.get(label, f'qdca_micros_fase_{label.lower()}')
        val = technical.get(key)
        if val not in (None, ''):
            any_set = True
            raw.append(_safe_int(val, 0))
        else:
            raw.append(None)

    if not any_set:
        return distribute_micros_across_phases(num_micros, len(labels)), False

    counts = [x if x is not None else 0 for x in raw]
    while len(counts) < len(labels):
        counts.append(0)
    return counts[: len(labels)], True


def parse_breaker_override(technical: dict[str, Any] | None, label: str) -> int | None:
    technical = technical or {}
    key = f'qdca_disj_fase_{label.lower()}'
    val = technical.get(key)
    if val in (None, ''):
        return None
    try:
        return int(float(str(val).replace(',', '.')))
    except (TypeError, ValueError):
        return None


def parse_bitola_override(technical: dict[str, Any] | None, label: str, default: str = '6') -> str:
    technical = technical or {}
    key = f'qdca_bitola_fase_{label.lower()}'
    val = technical.get(key) or technical.get('bitola_cabo_ca') or default
    return str(val).strip()


def _bitola_label(val: str) -> str:
    text = str(val or '').strip()
    if not text:
        return ''
    if 'mm' in text.lower():
        return text
    nums = re.findall(r'\d+(?:[.,]\d+)?', text)
    if nums:
        n = nums[0].replace(',', '.')
        if n.endswith('.0'):
            n = n[:-2]
        return f'{n} mm²'
    return text


def build_micro_qdca_layout(
    *,
    num_micros: int,
    power_per_micro_w: float,
    voltage_ln_v: float,
    network_type: str = 'trifasico',
    micros_per_breaker: int = 3,
    micros_per_phase: list[int] | None = None,
    breaker_overrides: dict[str, int] | None = None,
    bitola_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Monta layout QDCA micro — uma entrada por disjuntor (até 3 micros)."""
    labels = phase_labels_for_network(network_type)
    breaker_overrides = breaker_overrides or {}
    bitola_overrides = bitola_overrides or {}
    per_breaker = max(1, min(3, int(micros_per_breaker or 3)))

    if micros_per_phase is not None:
        manual = list(micros_per_phase[: len(labels)])
        while len(manual) < len(labels):
            manual.append(0)
        rows = pack_micro_breaker_rows(
            num_micros,
            power_per_micro_kw=power_per_micro_w / 1000,
            network_type=network_type,
            micros_per_breaker=per_breaker,
            manual_per_phase=manual,
            mode='balanceamento',
        )
    else:
        rows = pack_micro_breaker_rows(
            num_micros,
            power_per_micro_kw=power_per_micro_w / 1000,
            network_type=network_type,
            micros_per_breaker=per_breaker,
            mode='economia',
        )

    i_micro = power_per_micro_w / voltage_ln_v if voltage_ln_v else 0.0
    phase_details: list[dict[str, Any]] = []
    per_phase = [0] * len(labels)
    for row in rows:
        label = row['fase']
        idx = labels.index(label) if label in labels else 0
        per_phase[idx] += row['micros']
        br_a = breaker_overrides.get(label.upper()) or row['breaker_a']
        bitola = bitola_overrides.get(label.upper()) or bitola_overrides.get(label) or row['bitola_ca']
        phase_details.append({
            'fase': label,
            'micros': row['micros'],
            'groups': 1,
            'current_a': row['current_a'],
            'current_design_a': row['current_design_a'],
            'breaker_a': br_a,
            'breaker_calculated_a': row['breaker_a'],
            'bitola_ca': bitola,
        })

    lines = [
        f"Fase {d['fase']}: {d['micros']} micro-inversor(es), Disj {d['breaker_a']} A, cabo {_bitola_label(d['bitola_ca'])}"
        for d in phase_details
    ]
    worst_br = max((d['breaker_a'] for d in phase_details), default=40)
    i_worst = max((d['current_a'] for d in phase_details), default=0.0)

    layout = {
        'network_type': network_type,
        'labels': labels,
        'micros_per_phase': per_phase,
        'phase_details': phase_details,
        'num_qdca_breakers': len(phase_details),
        'num_dps': len(phase_details),
        'breaker_worst_a': worst_br,
        'current_per_micro_a': round(i_micro, 2),
        'current_worst_phase_a': i_worst,
        'description': '; '.join(lines),
        'qdca_summary': (
            f'QDCA com {len(phase_details)} disjuntor(es) e {len(phase_details)} DPS '
            f'(um par por fase alimentada).'
        ),
    }
    return layout


def build_micro_qdca_from_form(
    technical: dict[str, Any] | None,
    *,
    num_micros: int,
    power_per_micro_kw: float,
    voltage_ln_v: float,
    tipo_ligacao: str | None,
) -> dict[str, Any]:
    """Lê formulário e monta QDCA micro."""
    technical = technical or {}
    network = network_type_from_ligacao(tipo_ligacao)
    per_phase, manual = parse_user_micros_per_phase(
        technical, num_micros=num_micros, network_type=network,
    )
    total_user = sum(per_phase)
    use_manual = manual and total_user == num_micros
    if not use_manual and num_micros > 0:
        per_phase = None  # economia via pack_micro_breaker_rows

    overrides: dict[str, int] = {}
    bitola_overrides: dict[str, str] = {}
    for label in phase_labels_for_network(network):
        br = parse_breaker_override(technical, label)
        if br:
            overrides[label] = br
        bitola_overrides[label] = parse_bitola_override(technical, label)

    layout = build_micro_qdca_layout(
        num_micros=num_micros,
        power_per_micro_w=power_per_micro_kw * 1000,
        voltage_ln_v=voltage_ln_v,
        network_type=network,
        micros_per_breaker=_safe_int(technical.get('micros_por_grupo_ca'), 3) or 3,
        micros_per_phase=per_phase,
        breaker_overrides=overrides,
        bitola_overrides=bitola_overrides,
    )
    from protection_hierarchy import enrich_micro_layout_protection

    layout = enrich_micro_layout_protection(
        layout,
        technical,
        tipo_ligacao=tipo_ligacao,
        num_micros=num_micros,
        power_per_micro_kw=power_per_micro_kw,
    )
    num_dps = _safe_int(technical.get('qdca_num_dps'), 0)
    if num_dps > 0:
        layout['num_dps'] = num_dps
    obs = str(technical.get('qdca_observacoes') or '').strip()
    if obs:
        layout['qdca_summary'] = f"{layout['qdca_summary']} {obs}"
    return layout


def build_string_qdca_from_form(
    technical: dict[str, Any] | None,
    *,
    num_inverters: int,
    disjuntor_calc_a: int | None = None,
) -> dict[str, Any]:
    """QDCA para inversor string — disjuntor por inversor (editável)."""
    technical = technical or {}
    user_disj = _safe_int(technical.get('qdca_disjuntor_ca'), 0)
    disj = user_disj or disjuntor_calc_a or 40
    bitola = str(technical.get('qdca_bitola_ca') or technical.get('bitola_cabo_ca') or '6').strip()
    num = max(1, num_inverters)
    dps = _safe_int(technical.get('qdca_num_dps'), num)
    obs = str(technical.get('qdca_observacoes') or '').strip()
    summary = (
        f'QDCA: {num} disjuntor(es) CA de {disj} A (1 por inversor string) '
        f'e {dps} DPS CA — cabo {_bitola_label(bitola)}.'
    )
    if obs:
        summary = f'{summary} {obs}'
    layout = {
        'num_qdca_breakers': num,
        'num_dps': dps,
        'disjuntor_ca_a': disj,
        'bitola_ca': bitola,
        'qdca_summary': summary,
    }
    from protection_hierarchy import enrich_string_layout_protection

    power_kw = _safe_float(technical.get('potencia_inversor_kw'), 0)
    total_kw = _safe_float(technical.get('potencia_geracao_kw'), 0)
    if total_kw <= 0:
        total_kw = power_kw * num if power_kw > 0 else 6.0
    if power_kw <= 0:
        power_kw = total_kw / max(1, num)
    layout = enrich_string_layout_protection(
        layout,
        technical,
        power_kw=total_kw,
        tipo_ligacao=technical.get('tipo_ligacao'),
        inverter_fase=str(technical.get('inverter_fase_ca') or 'monofasico'),
        num_inverters=num,
        v_ln=_safe_float(technical.get('tensao_ln_v'), 220.0) or 220.0,
        v_ll=_safe_float(technical.get('tensao_ll_v'), 380.0) or 380.0,
    )
    return layout


def layout_to_tokens(layout: dict[str, Any], *, prefix: str = '') -> dict[str, str]:
    """Converte layout para tokens do memorial."""
    from protection_hierarchy import protection_layout_to_tokens

    tokens: dict[str, str] = {}
    tokens.update(protection_layout_to_tokens(layout))
    if layout.get('description'):
        tokens['DISTRIBUICAO_MICRO_FASES'] = layout['description']
    if layout.get('num_qdca_breakers') is not None:
        tokens['QTD_DISJUNTORES_QDCA'] = str(layout['num_qdca_breakers'])
    if layout.get('num_dps') is not None:
        tokens['QTD_DPS_QDCA'] = str(layout['num_dps'])
    if layout.get('qdca_summary'):
        tokens['TEXTO_QDCA_MICRO'] = layout['qdca_summary']
    if layout.get('protection_text'):
        tokens['PROTECAO_CA_DESCRICAO'] = layout['protection_text']
    if layout.get('disjuntor_ca_a'):
        tokens['DISJUNTOR_CA_INVERSOR_A'] = str(layout['disjuntor_ca_a'])
    for row in layout.get('phase_details') or []:
        fase = str(row.get('fase', '')).upper()
        if fase:
            tokens[f'QDCA_MICROS_FASE_{fase}'] = str(row.get('micros', ''))
            tokens[f'QDCA_DISJ_FASE_{fase}'] = str(row.get('breaker_a', ''))
            if row.get('bitola_ca'):
                tokens[f'QDCA_BITOLA_FASE_{fase}'] = _bitola_label(str(row.get('bitola_ca')))
    if layout.get('bitola_ca'):
        tokens['BITOLA_CABO_CA'] = _bitola_label(str(layout['bitola_ca']))
    return tokens


def layout_to_form_fields(layout: dict[str, Any]) -> dict[str, str]:
    """Sugestão de campos para preencher formulário após cálculo."""
    out: dict[str, str] = {}
    for row in layout.get('phase_details') or []:
        fase = str(row.get('fase', '')).upper()
        if fase:
            out[f'qdca_micros_fase_{fase.lower()}'] = str(row.get('micros', ''))
            out[f'qdca_disj_fase_{fase.lower()}'] = str(row.get('breaker_a', ''))
            if row.get('bitola_ca'):
                out[f'qdca_bitola_fase_{fase.lower()}'] = str(row.get('bitola_ca'))
    if layout.get('num_dps'):
        out['qdca_num_dps'] = str(layout['num_dps'])
    if layout.get('disjuntor_ca_a'):
        out['qdca_disjuntor_ca'] = str(layout['disjuntor_ca_a'])
    if layout.get('bitola_ca'):
        out['qdca_bitola_ca'] = str(layout['bitola_ca'])
    return out


def serialize_phase_details(layout: dict[str, Any]) -> str:
    return json.dumps(layout.get('phase_details') or [], ensure_ascii=False)
