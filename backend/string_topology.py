"""
Topologia MPPT / strings CC — usa dados do catálogo (strings por MPPT, Icc).
Regra PIENG: inversores até 10 kW monofásico 220 V; a partir de 12 kW trifásico.
"""

from __future__ import annotations

import json
import math
import re
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


def parse_strings_per_mppt(raw: Any, num_mppt: int = 1) -> list[int]:
    """Converte [1,1,1], '1+1', JSON ou int → lista por MPPT."""
    n = max(num_mppt, 1)
    if raw is None or raw == '':
        return [1] * n
    if isinstance(raw, list):
        nums = [max(1, _si(x, 1)) for x in raw if x not in (None, '')]
        if nums:
            if len(nums) < n:
                nums.extend([1] * (n - len(nums)))
            return nums[:n]
    if isinstance(raw, (int, float)):
        return [max(1, int(raw))] * n
    text = str(raw).strip()
    if text.startswith('['):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parse_strings_per_mppt(parsed, n)
        except json.JSONDecodeError:
            pass
    if '+' in text:
        parts = [p.strip() for p in text.split('+') if p.strip()]
        nums = [max(1, _si(p, 1)) for p in parts]
        if nums:
            if len(nums) < n:
                nums.extend([1] * (n - len(nums)))
            return nums[:n]
    if text.isdigit():
        return [int(text)] * n
    return [1] * n


def parse_icc_per_mppt(inverter: dict, strings_arr: list[int]) -> list[float]:
    raw = (
        inverter.get('icc_mppt_json')
        or inverter.get('corrente_entrada_cc_max_a_por_mppt')
        or inverter.get('corrente_max_cc_por_mppt')
    )
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith('['):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                raw = None
        elif '+' in text:
            raw = [float(x.strip()) for x in text.split('+') if x.strip()]
    if isinstance(raw, list) and raw:
        return [_sf(x) for x in raw]
    single = _sf(inverter.get('corrente_max_cc') or inverter.get('corrente_entrada_cc_max_a'))
    if single:
        return [single] * len(strings_arr)
    return [16.0] * len(strings_arr)


def series_module_bounds(
    voc: float,
    vmpp: float,
    mppt_min: float,
    mppt_max: float,
    vdc_max: float,
) -> tuple[int, int]:
    if vmpp <= 0:
        return 1, 24
    hi_vmpp = int(math.floor(mppt_max / vmpp)) if mppt_max else 24
    hi_voc = int(math.floor(vdc_max / voc)) if voc > 0 and vdc_max else hi_vmpp
    hi = max(1, min(hi_vmpp, hi_voc, 24))
    lo = max(1, int(math.ceil(mppt_min / vmpp))) if mppt_min else 1
    return lo, min(hi, lo + 20) if hi < lo else hi


def max_parallel_for_mppt(isc: float, icc_mppt: float) -> int:
    if isc <= 0 or icc_mppt <= 0:
        return 1
    return max(1, int(math.floor(icc_mppt / isc)))


def inverter_strings_per_mppt_from_catalog(inverter: dict) -> list[int]:
    num_mppt = _si(inverter.get('num_mppt'), 1) or 1
    raw = (
        inverter.get('strings_por_mppt_json')
        or inverter.get('strings_por_mppt')
        or inverter.get('strings_por_mppt_list')
    )
    return parse_strings_per_mppt(raw, num_mppt)


def suggest_string_layout(
    total_modules: int,
    inverter: dict,
    module: dict,
    *,
    inverter_qty: int = 1,
    user_modules_per_string: int = 0,
    user_strings_per_mppt: int = 0,
    topology: str = 'string',
) -> dict[str, Any]:
    """
    Sugere modulos_por_string, strings_count, strings_per_mppt e validações.
    Respeita entradas manuais da UI quando > 0.
    """
    messages: list[str] = []
    inv_qty = max(inverter_qty, 1)
    num_mppt = _si(inverter.get('num_mppt'), 2) or 2
    strings_per_mppt_arr = inverter_strings_per_mppt_from_catalog(inverter)
    icc_arr = parse_icc_per_mppt(inverter, strings_per_mppt_arr)

    voc = _sf(module.get('voc'))
    vmpp = _sf(module.get('vmpp'))
    isc = _sf(module.get('isc'))
    mppt_min = _sf(inverter.get('mppt_min'))
    mppt_max = _sf(inverter.get('mppt_max'))
    vdc_max = _sf(inverter.get('tensao_max_cc') or inverter.get('tensao_entrada_max_v'), 600)

    if topology == 'micro':
        return {
            'modules_per_string': 1,
            'strings_count': total_modules,
            'strings_per_mppt': 1,
            'num_mppt_per_inverter': num_mppt,
            'mppt_layout': strings_per_mppt_arr,
            'mppt_used': min(num_mppt, total_modules),
            'messages': messages,
            'icc_ok': True,
            'mppt_ok': True,
        }

    lo, hi = series_module_bounds(voc, vmpp, mppt_min, mppt_max, vdc_max)
    slots_per_inverter = sum(strings_per_mppt_arr)
    total_slots = max(slots_per_inverter * inv_qty, 1)
    pot_kw = _sf(inverter.get('potencia_kw') or inverter.get('potencia') or inverter.get('power'))
    mid_series = max(lo, (lo + hi) // 2) if hi else lo

    min_strings = 1
    if pot_kw and pot_kw <= 3.5:
        min_strings = 1
    elif total_slots >= 2 and total_modules >= 2 * lo:
        min_strings = min(total_slots, max(2, math.ceil(total_modules / max(mid_series, 1))))

    if user_modules_per_string > 0:
        modules_per_string = user_modules_per_string
        strings_count = max(1, math.ceil(total_modules / max(modules_per_string, 1)))
    else:
        strings_count = 1
        modules_per_string = total_modules
        best_score = None

        for candidate_strings in range(max(1, min_strings), total_slots + 1):
            if candidate_strings > total_modules:
                break
            mps = max(1, math.ceil(total_modules / candidate_strings))
            if mps < lo or mps > hi:
                continue
            remainder = (mps * candidate_strings) - total_modules
            if remainder < 0:
                continue
            penalty = abs(candidate_strings - min(total_slots, math.ceil(total_modules / max(mid_series, 1))))
            if pot_kw and pot_kw <= 3.5:
                penalty += candidate_strings * 2
            score = (penalty, mps, candidate_strings)
            if best_score is None or score < best_score:
                best_score = score
                strings_count = candidate_strings
                modules_per_string = mps

        if best_score is None:
            strings_count = max(1, min_strings)
            modules_per_string = max(1, math.ceil(total_modules / strings_count))

        if modules_per_string > hi:
            modules_per_string = hi
            strings_count = max(1, math.ceil(total_modules / hi))
            messages.append(f'Módulos/série limitados a {hi} (faixa MPPT / Vdc máx).')
        if modules_per_string < lo and lo <= hi:
            modules_per_string = lo
            strings_count = max(1, math.ceil(total_modules / lo))
            messages.append(f'Mínimo {lo} módulo(s) em série para MPPT mín ({mppt_min:g} V).')

    if user_strings_per_mppt > 0:
        strings_per_mppt = user_strings_per_mppt
    elif strings_count <= num_mppt * inv_qty:
        strings_per_mppt = max(1, math.ceil(strings_count / max(num_mppt * inv_qty, 1)))
    else:
        strings_per_mppt = max(strings_per_mppt_arr) if strings_per_mppt_arr else 1
    for idx, (slot_max, icc) in enumerate(zip(strings_per_mppt_arr, icc_arr)):
            allowed = min(slot_max, max_parallel_for_mppt(isc, icc))
            if strings_per_mppt > allowed:
                strings_per_mppt = allowed
                messages.append(
                    f'MPPT {idx + 1}: máx {allowed} string(s) em paralelo (Icc {icc:g} A, Isc {isc:g} A).'
                )

    icc_ok = True
    if isc > 0:
        for idx, icc in enumerate(icc_arr):
            if strings_per_mppt * isc > icc + 0.01:
                icc_ok = False
                messages.append(
                    f'Isc paralelo no MPPT {idx + 1}: {strings_per_mppt}×{isc:g} A = '
                    f'{strings_per_mppt * isc:.2f} A > limite {icc:g} A.'
                )

    string_voc = voc * modules_per_string if voc else 0
    string_vmpp = vmpp * modules_per_string if vmpp else 0
    mppt_ok = True
    if mppt_min and string_vmpp and string_vmpp < mppt_min:
        mppt_ok = False
        messages.append(f'Vmpp string ({string_vmpp:.1f} V) < MPPT mín ({mppt_min:g} V).')
    if mppt_max and string_voc and string_voc > mppt_max:
        mppt_ok = False
        messages.append(f'Voc string ({string_voc:.1f} V) > faixa MPPT máx ({mppt_max:g} V).')

    mppt_used = min(num_mppt, max(1, math.ceil(strings_count / max(strings_per_mppt, 1))))

    return {
        'modules_per_string': modules_per_string,
        'strings_count': strings_count,
        'strings_per_mppt': strings_per_mppt,
        'num_mppt_per_inverter': num_mppt,
        'mppt_layout': strings_per_mppt_arr,
        'icc_per_mppt': icc_arr,
        'mppt_used': mppt_used,
        'series_min': lo,
        'series_max': hi,
        'messages': messages,
        'icc_ok': icc_ok,
        'mppt_ok': mppt_ok,
        'string_voc_v': round(string_voc, 2),
        'string_vmpp_v': round(string_vmpp, 2),
    }
