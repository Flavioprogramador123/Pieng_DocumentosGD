"""
Análise de strings CC (NT.00020.EQTL / PRODIST 3).

Em série: soma-se tensão (Voc/Vmpp); corrente permanece (Isc/Impp).
Em paralelo (mesmo MPPT): tensão igual; soma-se corrente.

Micro-inversor (NT.00020.EQTL):
  - 1 módulo por entrada MPPT/string; equipamento junto ao módulo.
  - Tensão CC ≈ do módulo (dezenas de V); corrente ≈ Isc/Impp do módulo.
  - Até 3 micros em série por disjuntor CA (correntes CA somam).

Inversor string / central:
  - String com 2+ módulos em série (N×Vmpp, N×Voc); pode ultrapassar 1000 V CC.
  - Exige cuidados técnicos de proteção CC, seccionamento e aterramento.
  - Várias strings em paralelo por MPPT (limite Icc do fabricante).

Classificação micro × string: tipo do equipamento (catálogo/UI) e módulos/string —
não pela potência nominal em kW.
"""

from __future__ import annotations

import math
from typing import Any

from nbr5410_calculations import standard_breaker_rating
from string_topology import suggest_string_layout


def _enrich_inverter_from_catalog(inverter: dict) -> dict:
    """Completa topologia MPPT a partir do SQLite quando o formulário não traz."""
    if inverter.get('strings_por_mppt_json') or inverter.get('strings_por_mppt'):
        return inverter
    try:
        from catalog_db import catalog_inverter_to_specs, find_inverter_by_name_or_power

        fabricante = inverter.get('fabricante') or ''
        modelo = inverter.get('model') or inverter.get('modelo') or ''
        pot_kw = _sf(inverter.get('potencia') or inverter.get('power') or inverter.get('potencia_kw'))
        row = find_inverter_by_name_or_power(fabricante, modelo, pot_kw)
        if row:
            specs = catalog_inverter_to_specs(row)
            merged = {**inverter, **specs}
            if inverter.get('tipo_inversor'):
                merged['tipo_inversor'] = inverter['tipo_inversor']
            for key in ('strings_por_mppt_json', 'icc_mppt_json', 'micros_max_disjuntor_ca', 'fase_ca'):
                if row.get(key) is not None:
                    merged[key] = row[key]
            return merged
    except Exception:
        pass
    return inverter


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


def _tipo_inversor_is_micro(tipo: str | None) -> bool:
    t = (tipo or '').upper()
    return t in ('MICRO', 'MICROINVERSOR', 'MICRO-INVERSOR')


def _tipo_inversor_is_string(tipo: str | None) -> bool:
    t = (tipo or '').upper()
    return t in ('STRING', 'CENTRAL', 'STRING/MPPT', 'HIBRIDO', 'HÍBRIDO')


def _inverter_specs_indicate_micro(inverter: dict) -> bool:
    """Indícios de micro-inversor no catálogo/datasheet (não usa potência kW)."""
    if _tipo_inversor_is_micro(inverter.get('tipo_inversor')):
        return True
    if _tipo_inversor_is_string(inverter.get('tipo_inversor')):
        return False
    if inverter.get('micros_max_disjuntor_ca'):
        return True
    vdc_max = _sf(inverter.get('tensao_max_cc'))
    mppt_max = _sf(inverter.get('mppt_max'))
    # Micro: faixa CC baixa (ex. SAJ M2 Vdc máx 60 V, Vmppt 35–50 V)
    if vdc_max > 0 and vdc_max <= 80 and mppt_max > 0 and mppt_max <= 80:
        return True
    modelo = (inverter.get('model') or inverter.get('modelo') or '').upper()
    if 'MICRO' in modelo or 'M2-' in modelo or 'SUN2000' in modelo:
        return True
    return False


def label_tipo_equipamento_inversor(
    tipo_inversor: str | None = None,
    topology: str | None = None,
    modulos_por_string: int | None = None,
) -> str:
    """
    Rótulo curto para planta/memorial/DWG: 'Micro-inversor' ou 'Inversor'.
    Use {{TIPO_EQUIPAMENTO_INVERSOR}} nos templates (ex.: bloco técnico AutoCAD).

    Critério NT.00020.EQTL: micro = 1 módulo/MPPT (equipamento no módulo);
    inversor string = strings com 2+ módulos em série (tensões CC elevadas).
    """
    if modulos_por_string is not None and modulos_por_string > 1:
        return 'Inversor'
    if topology == 'micro' or _tipo_inversor_is_micro(tipo_inversor):
        return 'Micro-inversor'
    if topology == 'string' or _tipo_inversor_is_string(tipo_inversor):
        return 'Inversor'
    return 'Inversor'


def _detect_inverter_topology(
    inverter: dict,
    module_count: int,
    technical: dict | None = None,
) -> str:
    explicit_inv = (inverter.get('tipo_inversor') or inverter.get('topology') or '').upper()
    if _tipo_inversor_is_micro(explicit_inv):
        return 'micro'
    if _tipo_inversor_is_string(explicit_inv):
        return 'string'
    if technical:
        t = technical.get('tipo_inversor')
        if _tipo_inversor_is_micro(t):
            return 'micro'
        if _tipo_inversor_is_string(t):
            return 'string'

    user_mps = _si(technical.get('modulos_por_string')) if technical else 0
    # String com 2+ módulos em série — sempre inversor string (NT.00020.EQTL)
    if user_mps > 1:
        return 'string'

    if _inverter_specs_indicate_micro(inverter):
        return 'micro'

    # 1 módulo/string pode ser micro ou string com string única — prioriza catálogo/tipo
    if user_mps == 1 and module_count > _si(inverter.get('quantidade', inverter.get('quantity')), 1):
        # Vários módulos no sistema, 1 por string → layout típico de micro
        if _inverter_specs_indicate_micro(inverter):
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

    inv_ref = _enrich_inverter_from_catalog(inv_ref)

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
    catalog_micro_max = _si(inv_ref.get('micros_max_disjuntor_ca'), 0)
    if catalog_micro_max > 0 and topology == 'micro':
        micros_per_group = min(micros_per_group, catalog_micro_max)

    module_dict = {
        'voc': voc_mod,
        'isc': isc_mod,
        'vmpp': vmpp_mod,
        'impp': impp_mod,
    }

    layout = suggest_string_layout(
        total_modules,
        inv_ref,
        module_dict,
        inverter_qty=inv_qty,
        user_modules_per_string=user_mps,
        user_strings_per_mppt=user_spm,
        topology=topology,
    )
    messages.extend(layout.get('messages') or [])

    modules_per_string = layout['modules_per_string']
    strings_count = layout['strings_count']
    strings_per_mppt = layout['strings_per_mppt']
    mppt_layout = layout.get('mppt_layout') or []
    mppt_used = layout.get('mppt_used')
    icc_ok = layout.get('icc_ok', True)
    layout_mppt_ok = layout.get('mppt_ok', True)

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
        micro_groups = []
        num_ca_breakers = inv_qty
        layout_desc = '+'.join(str(x) for x in mppt_layout) if mppt_layout else str(strings_per_mppt)
        messages.append(
            f'Inversor string: {modules_per_string} módulo(s) em série por string; '
            f'{strings_count} string(s) no total; até {strings_per_mppt} string(s) em paralelo '
            f'por MPPT ({num_mppt} MPPT × {inv_qty} inversor(es)). '
            f'Topologia catálogo: {layout_desc}. '
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

    mppt_ok = layout_mppt_ok
    if mppt_min and string_vmpp and string_vmpp < mppt_min:
        mppt_ok = False
        if f'Vmpp string ({string_vmpp:.1f} V) < MPPT mín' not in ' '.join(messages):
            messages.append(f'Vmpp string ({string_vmpp:.1f} V) abaixo do MPPT mín ({mppt_min} V).')
    if mppt_max and string_voc and string_voc > mppt_max:
        mppt_ok = False
        if f'Voc string ({string_voc:.1f} V) > faixa MPPT' not in ' '.join(messages):
            messages.append(f'Voc string ({string_voc:.1f} V) acima do MPPT máx ({mppt_max} V).')

    status = 'OK'
    if not voc_mod or not isc_mod:
        status = 'ATENÇÃO'
    if not mppt_ok or not icc_ok:
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
        'mppt_layout': mppt_layout,
        'mppt_used': mppt_used,
        'icc_ok': icc_ok,
        'suggested_modulos_por_string': modules_per_string if not user_mps else None,
        'suggested_strings_por_mppt': strings_per_mppt if not user_spm else None,
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
