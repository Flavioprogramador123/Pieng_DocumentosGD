"""
Análise de strings CC: em série soma-se tensão (Voc/Vmpp), corrente permanece (Isc/Impp).
Microinversor: 1 módulo por MPPT; até 3 micros em série por disjuntor CA (correntes somam).
Inversor string: N módulos em série por string; várias strings em paralelo por MPPT.
"""

from __future__ import annotations

import math
from typing import Any

from nbr5410_calculations import standard_breaker_rating


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


def _detect_inverter_topology(
    inverter: dict,
    module_count: int,
    technical: dict | None = None,
) -> str:
    if technical:
        t = (technical.get('tipo_inversor') or '').upper()
        if t in ('MICRO', 'MICROINVERSOR', 'MICRO-INVERSOR'):
            return 'micro'
        if t in ('STRING', 'CENTRAL', 'STRING/MPPT'):
            return 'string'
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


def _modules_per_string(
    module_count: int,
    inverter_qty: int,
    num_mppt: int,
    topology: str,
    user_mps: int = 0,
) -> int:
    if topology == 'micro':
        return 1
    if user_mps > 0:
        return user_mps
    mppt_total = max(num_mppt * inverter_qty, 1)
    if module_count <= 0:
        return 0
    return max(1, math.ceil(module_count / mppt_total))


def _strings_per_mppt(
    strings_count: int,
    mppt_total: int,
    user_spm: int = 0,
) -> int:
    if user_spm > 0:
        return user_spm
    if mppt_total <= 0:
        return max(1, strings_count)
    return max(1, math.ceil(strings_count / mppt_total))


def _micro_groups(num_micros: int, micros_per_group: int) -> list[dict[str, Any]]:
    """Grupos de microinversores em série por disjuntor CA (máx. 3)."""
    per = max(1, min(3, micros_per_group))
    groups: list[dict[str, Any]] = []
    remaining = num_micros
    gid = 1
    while remaining > 0:
        count = min(per, remaining)
        remaining -= count
        groups.append({'group_id': gid, 'micros_count': count})
        gid += 1
    return groups


def analyze_dc_strings(modules: list, inverters: list, technical: dict | None = None) -> dict[str, Any]:
    """
    Calcula configuração de strings, correntes CC e textos para memorial/proteções.
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

    inv_ref = next(
        (i for i in (inverters or []) if _si(i.get('quantidade', i.get('quantity'))) > 0),
        None,
    )
    if not inv_ref:
        return {'status': 'ERRO', 'messages': ['Informe ao menos um inversor.'], 'strings': []}

    inv_qty = _si(inv_ref.get('quantidade', inv_ref.get('quantity')), 1)
    num_mppt = _si(inv_ref.get('num_mppt'), 0) or _si(technical.get('num_mppt'), 2)
    mppt_min = _sf(inv_ref.get('mppt_min'))
    mppt_max = _sf(inv_ref.get('mppt_max'))
    mppt_total = max(num_mppt * inv_qty, 1)

    topology = _detect_inverter_topology(inv_ref, total_modules, technical)
    user_mps = _si(technical.get('modulos_por_string'))
    user_spm = _si(technical.get('strings_por_mppt'))
    micros_per_group = _si(technical.get('micros_por_grupo_ca'), 3)
    if micros_per_group <= 0:
        micros_per_group = 3
    micros_per_group = min(3, micros_per_group)

    modules_per_string = _modules_per_string(
        total_modules, inv_qty, num_mppt, topology, user_mps,
    )

    if topology == 'micro':
        strings_count = total_modules
        modules_per_string = 1
        strings_per_mppt = 1
        micro_groups = _micro_groups(inv_qty, micros_per_group)
        num_ca_breakers = len(micro_groups)
        messages.append(
            f'Microinversor: 1 módulo por equipamento ({inv_qty} micro(s)); '
            f'proteção CA em {num_ca_breakers} disjuntor(es) — até {micros_per_group} micro(s) '
            f'em série por disjuntor (correntes somam no grupo).'
        )
        config_text = (
            f'Configuração CC: {total_modules} módulo(s) fotovoltaico(s) acoplados a '
            f'{inv_qty} microinversor(es) — 1 string por módulo (1 módulo/MPPT). '
            f'Voc por string = Voc do módulo ({voc_mod:g} V); Isc por string = Isc do módulo '
            f'({isc_mod:g} A). Strings independentes entre microinversores.'
        )
        i_micro_ca = _sf(inv_ref.get('corrente_max_saida_ca') or inv_ref.get('corrente_nominal'))
        prot_cc = (
            f'Proteção CC: cada microinversor com 1 string (1 módulo); dimensionamento de cabo CC '
            f'por Isc de projeto {isc_mod * 1.25:.2f} A (Isc {isc_mod:g} A × 1,25) por equipamento.'
        )
        if i_micro_ca:
            group_lines = []
            for g in micro_groups:
                i_g = i_micro_ca * g['micros_count']
                br = standard_breaker_rating(i_g * 1.25)
                group_lines.append(
                    f"Grupo {g['group_id']}: {g['micros_count']} micro(s) em série → "
                    f'{i_g:.2f} A → disjuntor {br} A'
                )
            prot_ca = (
                f'Proteção CA (QDCA): {num_ca_breakers} disjuntor(es) dedicado(s) — '
                f'até {micros_per_group} microinversor(es) em série por disjuntor. '
                + '; '.join(group_lines)
                + '.'
            )
        else:
            prot_ca = (
                f'Proteção CA (QDCA): {num_ca_breakers} disjuntor(es) — grupos de até '
                f'{micros_per_group} microinversor(es) em série por disjuntor (correntes somam).'
            )
    else:
        strings_count = max(1, math.ceil(total_modules / max(modules_per_string, 1)))
        strings_per_mppt = _strings_per_mppt(strings_count, mppt_total, user_spm)
        micro_groups = []
        num_ca_breakers = inv_qty
        messages.append(
            f'Inversor string: {modules_per_string} módulo(s) em série por string; '
            f'{strings_count} string(s) no total; até {strings_per_mppt} string(s) em paralelo '
            f'por entrada MPPT ({num_mppt} MPPT × {inv_qty} inversor(es)). '
            f'Isc da string = Isc do módulo (corrente NÃO soma em série).'
        )
        config_text = (
            f'Configuração CC: {total_modules} módulo(s) distribuídos em {strings_count} string(s) '
            f'de {modules_per_string} módulo(s) em série'
        )
        if strings_per_mppt > 1:
            config_text += f', com até {strings_per_mppt} string(s) em paralelo por entrada MPPT'
        config_text += (
            f' ({num_mppt} MPPT(s) por inversor × {inv_qty} inversor(es)). '
            f'Voc string = {voc_mod * modules_per_string:g} V; Isc string = {isc_mod:g} A.'
        )
        prot_cc = (
            f'Proteção CC: corrente de projeto por MPPT = Isc × strings em paralelo × 1,25 = '
            f'{isc_mod:g} A × {strings_per_mppt} × 1,25 = {isc_mod * strings_per_mppt * 1.25:.2f} A.'
        )
        prot_ca = (
            f'Proteção CA: {inv_qty} inversor(es) string — 1 disjuntor CA dedicado por inversor '
            f'(ou conforme QDCA do fabricante).'
        )

    string_voc = voc_mod * modules_per_string if voc_mod else 0
    string_vmpp = vmpp_mod * modules_per_string if vmpp_mod else 0
    string_isc = isc_mod
    string_impp = impp_mod if impp_mod else isc_mod

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

    cable_cc_note = (
        f'Bitola CC: dimensionar por Isc de projeto {isc_design_a:.1f} A '
        f'({strings_per_mppt} string(s) em paralelo × Isc {string_isc:.2f} A × 1,25).'
        if isc_design_a else 'Informe Isc para dimensionar cabo CC.'
    )

    return {
        'status': status,
        'topology': topology,
        'total_modules': total_modules,
        'inverter_quantity': inv_qty,
        'num_mppt_per_inverter': num_mppt,
        'mppt_total': mppt_total,
        'modules_per_string': modules_per_string,
        'strings_count': strings_count,
        'strings_per_mppt': strings_per_mppt,
        'micros_per_group_ca': micros_per_group if topology == 'micro' else None,
        'num_ca_breakers': num_ca_breakers,
        'micro_groups': micro_groups,
        'string_voc_v': round(string_voc, 2),
        'string_vmpp_v': round(string_vmpp, 2),
        'string_isc_a': round(string_isc, 2),
        'string_impp_a': round(string_impp, 2),
        'isc_design_a': round(isc_design_a, 2),
        'mppt_ok': mppt_ok,
        'messages': messages,
        'cable_cc_note': cable_cc_note,
        'configuracao_strings_text': config_text,
        'protecao_cc_text': prot_cc,
        'protecao_ca_text': prot_ca,
    }


def ac_current_a(power_kw: float, voltage_info: dict) -> float:
    """Corrente AC com fator √3 para trifásico (380 V LL em GO)."""
    power_w = power_kw * 1000
    v = voltage_info.get('voltage_v') or 220.0
    if voltage_info.get('system_type') == 'trifasico':
        return power_w / (v * math.sqrt(3)) if v else 0.0
    return power_w / v if v else 0.0
