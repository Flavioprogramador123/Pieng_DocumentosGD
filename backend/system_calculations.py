"""
Cálculos completos do sistema fotovoltaico para a aba Cálculos do frontend.
"""

from __future__ import annotations

import math
import re
from typing import Any

from advanced_calculations import (
    calculate_cable_section_advanced,
    calculate_energy_generation,
    calculate_protection_devices_advanced,
)
from demand_table import generate_demand_table
from grid_voltage import resolve_ac_voltage
from string_calculations import ac_current_a, analyze_dc_strings


def _parse_voltage(text: str | None) -> float:
    if not text:
        return 220.0
    match = re.search(r'(\d{2,3})', str(text))
    if match:
        return float(match.group(1))
    return 220.0


def _safe_float(value, default: float = 0.0) -> float:
    if value in (None, ''):
        return default
    try:
        return float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    if value in (None, ''):
        return default
    try:
        return int(float(str(value).replace(',', '.')))
    except (TypeError, ValueError):
        return default


def _map_system_type(tipo_ligacao: str | None) -> str:
    t = (tipo_ligacao or '').upper()
    if 'TRIF' in t:
        return 'trifasico'
    if 'BIF' in t:
        return 'bifasico'
    return 'monofasico'


def calculate_technical_parameters(modules, inverters, context: dict | None = None) -> dict[str, Any]:
    """
    Calcula parâmetros técnicos completos.
    Módulos em W (Wp), inversores em kW.
    """
    context = context or {}
    client = context.get('client') or {}
    technical = context.get('technical') or {}

    total_module_power_w = sum(
        _safe_int(m.get('quantidade', m.get('quantity')))
        * _safe_float(m.get('potencia', m.get('power')))
        for m in (modules or [])
        if _safe_int(m.get('quantidade', m.get('quantity'))) > 0
        and _safe_float(m.get('potencia', m.get('power'))) > 0
    )
    total_module_power_kw = total_module_power_w / 1000

    total_inverter_power_kw = sum(
        _safe_int(i.get('quantidade', i.get('quantity')))
        * _safe_float(i.get('potencia', i.get('power')))
        for i in (inverters or [])
        if _safe_int(i.get('quantidade', i.get('quantity'))) > 0
        and _safe_float(i.get('potencia', i.get('power'))) > 0
    )

    hsp = float(context.get('hsp') or 5.2)
    efficiency = 0.80
    days_per_month = 30.4
    estimated_monthly = total_module_power_kw * hsp * efficiency * days_per_month
    estimated_annual = estimated_monthly * 12
    estimated_daily = estimated_monthly / days_per_month

    relacao = (
        total_module_power_kw / total_inverter_power_kw
        if total_inverter_power_kw > 0 else 0
    )

    if total_module_power_kw <= 5:
        cable_cc, cable_ca = '6mm²', '10mm²'
    elif total_module_power_kw <= 10:
        cable_cc, cable_ca = '10mm²', '16mm²'
    elif total_module_power_kw <= 20:
        cable_cc, cable_ca = '16mm²', '25mm²'
    else:
        cable_cc, cable_ca = '25mm²', '35mm²'

    voltage_info = resolve_ac_voltage(
        uf=client.get('uf'),
        tipo_ligacao=client.get('tipo_ligacao'),
        tensao_atendimento=client.get('tensao_atendimento') or technical.get('tensao_atendimento'),
    )
    voltage = voltage_info['voltage_v']
    system_type = voltage_info['system_type']
    power_w = max(total_inverter_power_kw, total_module_power_kw) * 1000

    dc_strings = analyze_dc_strings(modules or [], inverters or [], technical)
    corrente_ac = ac_current_a(total_inverter_power_kw, voltage_info)

    disjuntor_recomendado = max(10, int(math.ceil(corrente_ac * 1.25))) if corrente_ac else 0
    tarifa = 1.10
    economia_mensal = estimated_monthly * tarifa

    generation_detail = calculate_energy_generation(modules or [])
    cables_detail = calculate_cable_section_advanced(power_w, voltage)
    protection_detail = calculate_protection_devices_advanced(power_w, voltage, system_type)

    # Cabo CC: preferir Isc de projeto das strings (paralelo), não soma errada de módulos
    if dc_strings.get('isc_design_a'):
        isc = dc_strings['isc_design_a']
        cable_cc = '6mm²' if isc <= 15 else '10mm²' if isc <= 25 else '16mm²'
    else:
        cable_cc = cable_cc  # noqa: keep heuristic from power tier above

    compatibility_status = 'OK'
    compatibility_messages = []
    if total_inverter_power_kw <= 0 or total_module_power_kw <= 0:
        compatibility_status = 'ERRO'
        compatibility_messages.append('Informe módulos e inversores com potência válida.')
    elif relacao < 1.05:
        compatibility_status = 'ATENÇÃO'
        compatibility_messages.append(f'Relação DC/AC baixa ({relacao:.2f}). Ideal: 1,10–1,30.')
    elif relacao > 1.35:
        compatibility_status = 'ATENÇÃO'
        compatibility_messages.append(f'Relação DC/AC alta ({relacao:.2f}). Verificar clipping.')
    else:
        compatibility_messages.append('Relação módulo/inversor dentro da faixa usual (1,10–1,30).')

    compatibility_messages.extend(dc_strings.get('messages') or [])
    if dc_strings.get('status') == 'ATENÇÃO' and compatibility_status == 'OK':
        compatibility_status = 'ATENÇÃO'
    if dc_strings.get('status') == 'ERRO':
        compatibility_status = 'ERRO'

    result: dict[str, Any] = {
        'total_module_power_kw': round(total_module_power_kw, 2),
        'total_inverter_power_kw': round(total_inverter_power_kw, 2),
        'relacao_modulo_inversor': round(relacao, 2),
        'estimated_monthly_generation': round(estimated_monthly, 0),
        'estimated_annual_generation': round(estimated_annual, 0),
        'estimated_daily_generation': round(estimated_daily, 1),
        'hsp_used': hsp,
        'system_efficiency_pct': round(efficiency * 100, 0),
        'voltage_v': voltage,
        'voltage_info': voltage_info,
        'system_type': system_type,
        'corrente_ac_a': round(corrente_ac, 2),
        'dc_strings': dc_strings,
        'cable_section_cc': cable_cc,
        'cable_section_ca': cable_ca,
        'disjuntor_recomendado_a': disjuntor_recomendado,
        'economia_mensal_estimada': round(economia_mensal, 2),
        'tarifa_kwh': tarifa,
        'power_summary': {
            'total_module_power_kw': round(total_module_power_kw, 2),
            'total_inverter_power_kw': round(total_inverter_power_kw, 2),
            'power_ratio': round(relacao, 2),
        },
        'generation': {
            'monthly_generation_kwh': round(estimated_monthly, 0),
            'annual_generation_kwh': round(estimated_annual, 0),
            'daily_generation_kwh': round(estimated_daily, 1),
            'irradiation_kwh_m2_day': generation_detail.get('irradiation_kwh_m2_day'),
            'performance_ratio': generation_detail.get('performance_ratio'),
        },
        'cables': {
            'recommended_cc': cable_cc,
            'recommended_ca': cable_ca,
            'detail': cables_detail,
        },
        'protection': protection_detail,
        'compatibility': {
            'status': compatibility_status,
            'message': compatibility_messages[0] if compatibility_messages else '',
            'warnings': [m for m in compatibility_messages if compatibility_status != 'OK'],
            'errors': [m for m in compatibility_messages if compatibility_status == 'ERRO'],
        },
        'all_items': [],
    }

    result['all_items'] = _build_all_items(result)

    demanda_raw = (
        technical.get('demanda_alvo_kw')
        or context.get('demanda_alvo_kw')
        or client.get('demanda_alvo_kw')
    )
    if demanda_raw not in (None, ''):
        try:
            target = float(str(demanda_raw).replace(',', '.'))
            prefer_ai = bool(context.get('demand_table_ai'))
            result['demand_table'] = generate_demand_table(
                target_kw=target,
                classe=client.get('classe') or 'INDUSTRIAL',
                client_name=client.get('client_name') or client.get('nome') or '',
                uc=client.get('consumer_unit') or client.get('numero') or '',
                notes=technical.get('demanda_notas') or '',
                prefer_ai=prefer_ai,
            )
        except (TypeError, ValueError) as exc:
            result['demand_table_error'] = str(exc)

    return result


def _build_all_items(calc: dict) -> list[dict]:
    """Lista plana de todos os cálculos para exibição na UI."""
    items = [
        {'grupo': 'Potência', 'rotulo': 'Potência total módulos', 'valor': f"{calc['total_module_power_kw']} kWp", 'token': 'POTENCIA_TOTAL_INSTALADA'},
        {'grupo': 'Potência', 'rotulo': 'Potência total inversores', 'valor': f"{calc['total_inverter_power_kw']} kW", 'token': 'POTENCIA_INVERSOR_TOTAL'},
        {'grupo': 'Potência', 'rotulo': 'Relação DC/AC', 'valor': str(calc['relacao_modulo_inversor']), 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Geração mensal estimada', 'valor': f"{calc['estimated_monthly_generation']} kWh/mês", 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Geração anual estimada', 'valor': f"{calc['estimated_annual_generation']} kWh/ano", 'token': None},
        {'grupo': 'Geração', 'rotulo': 'HSP utilizado', 'valor': f"{calc['hsp_used']} h/dia", 'token': None},
        {'grupo': 'Elétrico', 'rotulo': 'Tensão de cálculo', 'valor': f"{calc['voltage_v']} V ({calc.get('voltage_info', {}).get('note', '')})", 'token': 'TENSAO_ATENDIMENTO'},
        {'grupo': 'Elétrico', 'rotulo': 'Fórmula corrente AC', 'valor': calc.get('voltage_info', {}).get('formula', '—'), 'token': None},
        {'grupo': 'Elétrico', 'rotulo': 'Corrente AC estimada', 'valor': f"{calc['corrente_ac_a']} A", 'token': 'CORRENTE_ENTRADA'},
        {'grupo': 'Elétrico', 'rotulo': 'Disjuntor recomendado', 'valor': f"{calc['disjuntor_recomendado_a']} A", 'token': 'DISJUNTOR_ENTRADA'},
        {'grupo': 'Cabos', 'rotulo': 'Bitola CC recomendada', 'valor': calc['cable_section_cc'], 'token': 'BITOLA_CABO_CC'},
        {'grupo': 'Cabos', 'rotulo': 'Bitola CA recomendada', 'valor': calc['cable_section_ca'], 'token': 'BITOLA_CABO_CA'},
        {'grupo': 'Economia', 'rotulo': 'Economia mensal estimada', 'valor': f"R$ {calc['economia_mensal_estimada']}", 'token': None},
    ]
    dc = calc.get('dc_strings') or {}
    if dc:
        items.extend([
            {'grupo': 'Strings CC', 'rotulo': 'Topologia', 'valor': dc.get('topology', '—'), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Módulos/string', 'valor': str(dc.get('modules_per_string', '—')), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Voc string (série)', 'valor': f"{dc.get('string_voc_v', '—')} V", 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Isc string (= módulo)', 'valor': f"{dc.get('string_isc_a', '—')} A", 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Isc projeto (×1,25)', 'valor': f"{dc.get('isc_design_a', '—')} A", 'token': None},
        ])
    prot = calc.get('protection') or {}
    if prot:
        items.extend([
            {'grupo': 'Proteção', 'rotulo': 'Disjuntor CA (detalhe)', 'valor': f"{prot.get('ac_breaker_a')} A", 'token': None},
            {'grupo': 'Proteção', 'rotulo': 'DPS', 'valor': f"{prot.get('dps_class')} {prot.get('dps_voltage')}", 'token': None},
        ])
    cab = calc.get('cables', {}).get('detail') or {}
    if cab:
        items.append({
            'grupo': 'Cabos',
            'rotulo': 'Seção calculada (NR)',
            'valor': f"{cab.get('recommended_section_mm2')} mm²",
            'token': None,
        })
    return items
