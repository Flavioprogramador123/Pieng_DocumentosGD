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
from grid_voltage import resolve_ac_voltage, map_inverter_fase, resolve_ligacao_config
from nbr5410_calculations import (
    calculate_inverter_ac_current,
    validate_inverter_network_compatibility,
    validate_network_power_limit,
    calculate_breaker_groups_microinverters,
)
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


def _parse_bitola_mm2(val: Any) -> float | None:
    if val is None or str(val).strip() == '':
        return None
    match = re.search(r'([\d]+(?:[.,]\d+)?)', str(val))
    if not match:
        return None
    try:
        return float(match.group(1).replace(',', '.'))
    except ValueError:
        return None


def _validate_user_cables(
    technical: dict,
    recommended_cc: str,
    recommended_ca: str,
    recommended_padrao: str | None = None,
) -> list[str]:
    """Compara bitolas informadas pelo usuário com as recomendadas — só alerta, não altera."""
    warnings: list[str] = []
    checks = [
        ('bitola_cabo_cc', recommended_cc, 'CC (inversor)'),
        ('bitola_cabo_ca', recommended_ca, 'CA (inversor)'),
    ]
    if recommended_padrao:
        checks.append(('bitola_cabo_padrao', recommended_padrao, 'padrão de entrada'))

    for field, recommended, label in checks:
        user_mm = _parse_bitola_mm2(technical.get(field))
        rec_mm = _parse_bitola_mm2(recommended)
        if user_mm is None or rec_mm is None:
            continue
        if user_mm < rec_mm:
            warnings.append(
                f'Cabo {label}: informado {user_mm:g} mm², recomendado {rec_mm:g} mm² '
                f'(abaixo do sugerido — confira NBR 5410).'
            )
        elif user_mm > rec_mm:
            warnings.append(
                f'Cabo {label}: informado {user_mm:g} mm², recomendado {rec_mm:g} mm² '
                f'(acima do mínimo — OK se conferido).'
            )
    return warnings


def _resolve_inverter_fase(inverters, technical, topology: str) -> str:
    """Fase CA do inversor (monofasico/bifasico/trifasico). Micro → monofásico."""
    if topology == 'micro':
        return 'monofasico'
    for inv in (inverters or []):
        fc = inv.get('fase_ca')
        if fc:
            return map_inverter_fase(fc)
    fc_tech = (technical or {}).get('fase_ca')
    if fc_tech:
        return map_inverter_fase(fc_tech)
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

    hsp = float(context.get('hsp') or 0)
    gen_params = None
    try:
        from app_settings import compute_monthly_generation_kwh, get_generation_params
        gen_params = get_generation_params(client.get('uf'))
        if hsp <= 0:
            hsp = gen_params['hsp']
    except ImportError:
        if hsp <= 0:
            try:
                from normas_loader import get_hsp
                hsp = get_hsp(client.get('uf'))
            except Exception:
                hsp = 5.30
    efficiency = gen_params['eficiencia_sistema'] if gen_params else 0.80
    days_per_month = gen_params['dias_por_mes'] if gen_params else 30.4
    tarifa = gen_params['tarifa_kwh'] if gen_params else 1.10

    if gen_params and total_module_power_kw > 0:
        gen_calc = compute_monthly_generation_kwh(total_module_power_kw, client.get('uf'))
        estimated_monthly = gen_calc['monthly_kwh']
        estimated_annual = gen_calc['annual_kwh']
        estimated_daily = gen_calc['daily_kwh']
        generation_formula = gen_calc['formula_expanded']
    else:
        estimated_monthly = total_module_power_kw * hsp * efficiency * days_per_month
        estimated_annual = estimated_monthly * 12
        estimated_daily = estimated_monthly / days_per_month
        generation_formula = (
            f'E_mês = {total_module_power_kw:g} kWp × {hsp:g} h/dia × '
            f'{efficiency:g} × {days_per_month:g} dias = {estimated_monthly:.0f} kWh/mês'
        )

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

    try:
        from normas_loader import get_bitola_ca, get_bitola_cc
        cable_cc = get_bitola_cc(total_module_power_kw).replace(' ', '')
        cable_ca = get_bitola_ca(total_inverter_power_kw).replace(' ', '')
    except Exception:
        pass

    voltage_info = resolve_ac_voltage(
        uf=client.get('uf'),
        tipo_ligacao=client.get('tipo_ligacao'),
        tensao_atendimento=client.get('tensao_atendimento') or technical.get('tensao_atendimento'),
    )
    voltage_ll = voltage_info['voltage_ll_v']
    voltage_ln = voltage_info['voltage_ln_v']
    system_type = voltage_info['system_type']
    ligacao_rede = resolve_ligacao_config(client.get('tipo_ligacao'))
    power_w = max(total_inverter_power_kw, total_module_power_kw) * 1000

    disjuntor_padrao_a = _safe_float(
        technical.get('disjuntor_entrada') or client.get('disjuntor_entrada'),
        40.0,
    )

    dc_strings = analyze_dc_strings(modules or [], inverters or [], technical)

    topology = dc_strings.get('topology', 'string')
    num_inverters = dc_strings.get('inverter_quantity', 1)
    inverter_fase = _resolve_inverter_fase(inverters, technical, topology)

    inverter_ac = calculate_inverter_ac_current(
        power_kw=total_inverter_power_kw,
        inverter_fase=inverter_fase,
        voltage_ln_v=voltage_ln,
        voltage_ll_v=voltage_ll,
        topology=topology,
        num_devices=num_inverters,
    )

    corrente_inversor_a = inverter_ac['current_nominal_a']
    disjuntor_inversor_a = inverter_ac['breaker_rated_a']
    v_calc = voltage_ln if inverter_fase == 'monofasico' or topology == 'micro' else voltage_ll

    # Validar compatibilidade inversor × rede
    network_compatibility = validate_inverter_network_compatibility(
        inverter_type=inverter_fase,
        network_type=system_type,
        topology=topology,
    )

    # Validar limite de potência da rede
    power_limit = validate_network_power_limit(
        power_kw=total_inverter_power_kw,
        voltage_v=voltage_ll,
        system_type=system_type,
    )

    # Disjuntores CA conforme topologia (micro: grupos até 3 em série; string: 1 por inversor)
    if topology == 'micro' and num_inverters > 0:
        power_per_micro = (total_inverter_power_kw * 1000) / num_inverters
        breaker_groups_info = calculate_breaker_groups_microinverters(
            num_microinverters=num_inverters,
            power_per_micro_w=power_per_micro,
            voltage_v=v_calc,
        )
        # Respeitar agrupamento informado pelo usuário (1–3 micros/disjuntor)
        user_group = _safe_int(technical.get('micros_por_grupo_ca'), 3) or 3
        user_group = min(3, max(1, user_group))
        if user_group != 3:
            micro_groups = dc_strings.get('micro_groups') or []
            breaker_groups_info = {
                'num_breakers': len(micro_groups) or breaker_groups_info['num_breakers'],
                'breaker_groups': breaker_groups_info.get('breaker_groups') or [],
                'total_breakers_detail': (
                    f'{len(micro_groups)} disjuntor(es) CA — até {user_group} micro(s) em série por disjuntor'
                ),
            }
        num_breakers_ca = dc_strings.get('num_ca_breakers') or breaker_groups_info['num_breakers']
    else:
        num_breakers_ca = num_inverters
        breaker_groups_info = {
            'num_breakers': num_inverters,
            'breaker_groups': [],
            'total_breakers_detail': f'{num_inverters} disjuntor(es) CA (1 por inversor string)',
        }

    breaker_result = {'breaker_rated_a': disjuntor_inversor_a}
    disjuntor_recomendado = disjuntor_inversor_a
    tarifa = tarifa if gen_params else 1.10
    economia_mensal = estimated_monthly * tarifa

    generation_detail = calculate_energy_generation(modules or [])
    cables_detail = calculate_cable_section_advanced(power_w, v_calc)
    protection_detail = calculate_protection_devices_advanced(power_w, v_calc, system_type)

    # Cabo CC: preferir Isc de projeto das strings (paralelo), não soma errada de módulos
    if dc_strings.get('isc_design_a'):
        isc = dc_strings['isc_design_a']
        try:
            from normas_loader import get_bitola_cc
            cable_cc = get_bitola_cc(total_module_power_kw, isc_a=isc).replace(' ', '')
        except Exception:
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

    # Adicionar avisos do inversor
    compatibility_messages.extend(inverter_ac.get('warnings') or [])
    if inverter_ac.get('warnings') and compatibility_status == 'OK':
        compatibility_status = 'ATENÇÃO'

    # Adicionar compatibilidade de rede
    if not network_compatibility['compatible']:
        compatibility_status = 'ERRO'
        compatibility_messages.append(network_compatibility['message'])
    else:
        compatibility_messages.append(network_compatibility['message'])

    # Adicionar validação de limite de potência
    if not power_limit['valid']:
        compatibility_status = 'ERRO'
        compatibility_messages.append(power_limit['message'])
    else:
        compatibility_messages.append(power_limit['message'])

    recommended_padrao = None
    try:
        from normas_loader import get_bitola_padrao
        idg = float(
            str(
                technical.get('disjuntor_entrada')
                or client.get('disjuntor_entrada')
                or '40'
            ).replace(',', '.')
        )
        recommended_padrao = get_bitola_padrao(idg)
    except (TypeError, ValueError):
        recommended_padrao = '10 mm²'

    cable_warnings = _validate_user_cables(
        technical, cable_cc, cable_ca, recommended_padrao,
    )
    if cable_warnings:
        compatibility_messages.extend(cable_warnings)
        if compatibility_status == 'OK':
            compatibility_status = 'ATENÇÃO'

    grid_padrao = {
        'tipo_rede': ligacao_rede['tipo_rede'],
        'system_type': system_type,
        'voltage_ln_v': voltage_ln,
        'voltage_ll_v': voltage_ll,
        'disjuntor_entrada_a': int(disjuntor_padrao_a) if disjuntor_padrao_a else 40,
        'num_polos_disjuntor': ligacao_rede['num_polos_disjuntor'],
        'descricao_polos': ligacao_rede['descricao_polos'],
        'descricao_disjuntor_padrao': ligacao_rede['descricao_disjuntor_padrao'],
        'note': voltage_info.get('note', ''),
    }

    result: dict[str, Any] = {
        'total_module_power_kw': round(total_module_power_kw, 2),
        'total_inverter_power_kw': round(total_inverter_power_kw, 2),
        'relacao_modulo_inversor': round(relacao, 2),
        'estimated_monthly_generation': round(estimated_monthly, 0),
        'estimated_annual_generation': round(estimated_annual, 0),
        'estimated_daily_generation': round(estimated_daily, 1),
        'hsp_used': hsp,
        'generation_formula': generation_formula,
        'system_efficiency_pct': round(efficiency * 100, 0),
        'voltage_v': voltage_ll,
        'voltage_info': voltage_info,
        'system_type': system_type,
        'inverter_fase': inverter_fase,
        'inverter_ac': inverter_ac,
        'grid_padrao': grid_padrao,
        'corrente_inversor_a': round(corrente_inversor_a, 2),
        'disjuntor_inversor_ca_a': disjuntor_inversor_a,
        'corrente_ac_a': round(corrente_inversor_a, 2),
        'corrente_por_fase_a': round(inverter_ac['current_per_phase_a'], 2),
        'ac_current_nbr5410': inverter_ac,
        'network_compatibility': network_compatibility,
        'power_limit': power_limit,
        'num_breakers_ca': num_breakers_ca,
        'breaker_groups': breaker_groups_info,
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
            'recommended_padrao': recommended_padrao,
            'detail': cables_detail,
        },
        'cable_warnings': cable_warnings,
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
    modelo_id = technical.get('demanda_modelo_id') or context.get('demanda_modelo_id')
    if demanda_raw not in (None, '') or modelo_id:
        try:
            if modelo_id:
                from demand_presets import generate_from_model
                target = None
                if demanda_raw not in (None, ''):
                    target = float(str(demanda_raw).replace(',', '.'))
                result['demand_table'] = generate_from_model(
                    modelo_id,
                    client_name=client.get('client_name') or client.get('nome') or '',
                    uc=client.get('consumer_unit') or client.get('numero') or '',
                    target_kw=target,
                    notes=technical.get('demanda_notas') or '',
                )
            else:
                target = float(str(demanda_raw).replace(',', '.'))
                prefer_ai = bool(context.get('demand_table_ai'))
                result['demand_table'] = generate_demand_table(
                    target_kw=target,
                    classe=client.get('classe') or 'RESIDENCIAL',
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
    inv = calc.get('inverter_ac') or {}
    grid = calc.get('grid_padrao') or {}
    inv_fase = calc.get('inverter_fase', 'monofasico')

    items = [
        {'grupo': 'Potência', 'rotulo': 'Potência total módulos', 'valor': f"{calc['total_module_power_kw']} kWp", 'token': 'POTENCIA_TOTAL_INSTALADA'},
        {'grupo': 'Potência', 'rotulo': 'Potência total inversores', 'valor': f"{calc['total_inverter_power_kw']} kW", 'token': 'POTENCIA_INVERSOR_TOTAL'},
        {'grupo': 'Potência', 'rotulo': 'Relação DC/AC', 'valor': str(calc['relacao_modulo_inversor']), 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Geração mensal estimada', 'valor': f"{calc['estimated_monthly_generation']} kWh/mês", 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Geração anual estimada', 'valor': f"{calc['estimated_annual_generation']} kWh/ano", 'token': None},
        {'grupo': 'Geração', 'rotulo': 'HSP utilizado', 'valor': f"{calc['hsp_used']} h/dia", 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Fórmula geração mensal', 'valor': calc.get('generation_formula', '—'), 'token': None},
        {'grupo': 'Geração', 'rotulo': 'Eficiência do sistema (η)', 'valor': f"{calc.get('system_efficiency_pct', 80)} %", 'token': None},
    ]

    # —— Padrão de entrada (rede concessionária — não depende do inversor) ——
    if grid:
        tensao_padrao = (
            f"VN = {grid.get('voltage_ln_v', '—')} V, V_LL = {grid.get('voltage_ll_v', '—')} V "
            f"({grid.get('note', '')})"
            if grid.get('system_type') == 'trifasico'
            else f"{grid.get('voltage_ln_v', '—')} V ({grid.get('note', '')})"
        )
        items.extend([
            {'grupo': 'Padrão de entrada', 'rotulo': 'Tipo de rede (UC)', 'valor': grid.get('tipo_rede', '—'), 'token': 'TIPO_REDE'},
            {'grupo': 'Padrão de entrada', 'rotulo': 'Tensão concessionária', 'valor': tensao_padrao, 'token': 'TENSAO_ATENDIMENTO'},
            {'grupo': 'Padrão de entrada', 'rotulo': 'Disjuntor geral (informado)', 'valor': f"{grid.get('disjuntor_entrada_a', '—')} A", 'token': 'DISJUNTOR_ENTRADA'},
            {'grupo': 'Padrão de entrada', 'rotulo': 'Disjuntor padrão (polos)', 'valor': f"{grid.get('descricao_polos', '—')} ({grid.get('num_polos_disjuntor', '—')} polos)", 'token': 'DESCRICAO_POLOS_DISJUNTOR'},
        ])

    # —— Inversor CA (potência nominal × fase do equipamento) ——
    fase_label = {'monofasico': 'Monofásico', 'trifasico': 'Trifásico', 'bifasico': 'Bifásico'}.get(inv_fase, inv_fase)
    items.extend([
        {'grupo': 'Inversor CA', 'rotulo': 'Fase CA do inversor', 'valor': fase_label, 'token': 'FASE_CA'},
        {'grupo': 'Inversor CA', 'rotulo': 'Potência nominal CA', 'valor': f"{calc['total_inverter_power_kw']} kW", 'token': 'POTENCIA_INVERSOR_TOTAL'},
        {'grupo': 'Inversor CA', 'rotulo': 'Fórmula corrente', 'valor': inv.get('formula', '—'), 'token': None},
        {'grupo': 'Inversor CA', 'rotulo': 'Corrente nominal inversor', 'valor': f"{calc.get('corrente_inversor_a', '—')} A", 'token': None},
        {'grupo': 'Inversor CA', 'rotulo': 'Corrente projeto (×1,25)', 'valor': f"{inv.get('current_design_a', '—')} A", 'token': None},
        {'grupo': 'Inversor CA', 'rotulo': 'Disjuntor CA inversor', 'valor': f"{calc.get('disjuntor_inversor_ca_a', '—')} A {inv.get('descricao_polos_disjuntor', '')}", 'token': 'DISJUNTOR_CA_INVERSOR_A'},
        {'grupo': 'Inversor CA', 'rotulo': 'Conexão', 'valor': inv.get('distribution', '—'), 'token': None},
        {'grupo': 'Inversor CA', 'rotulo': 'Qtd disjuntores CA', 'valor': str(calc.get('num_breakers_ca', '—')), 'token': None},
        {'grupo': 'Cabos', 'rotulo': 'Bitola CC recomendada', 'valor': calc['cable_section_cc'], 'token': 'BITOLA_CABO_CC'},
        {'grupo': 'Cabos', 'rotulo': 'Bitola CA inversor', 'valor': calc['cable_section_ca'], 'token': 'BITOLA_CABO_CA'},
        {'grupo': 'Economia', 'rotulo': 'Economia mensal estimada', 'valor': f"R$ {calc['economia_mensal_estimada']}", 'token': None},
    ])
    dc = calc.get('dc_strings') or {}
    if dc:
        items.extend([
            {'grupo': 'Strings CC', 'rotulo': 'Topologia', 'valor': dc.get('topology', '—'), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Módulos/string', 'valor': str(dc.get('modules_per_string', '—')), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Strings/MPPT (paralelo)', 'valor': str(dc.get('strings_per_mppt', '—')), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Total strings', 'valor': str(dc.get('strings_count', '—')), 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Voc string (série)', 'valor': f"{dc.get('string_voc_v', '—')} V", 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Isc string (= módulo)', 'valor': f"{dc.get('string_isc_a', '—')} A", 'token': None},
            {'grupo': 'Strings CC', 'rotulo': 'Isc projeto (×1,25)', 'valor': f"{dc.get('isc_design_a', '—')} A", 'token': None},
        ])
        if dc.get('configuracao_strings_text'):
            items.append({
                'grupo': 'Strings CC',
                'rotulo': 'Texto memorial (config.)',
                'valor': dc['configuracao_strings_text'][:120] + '…' if len(dc['configuracao_strings_text']) > 120 else dc['configuracao_strings_text'],
                'token': 'CONFIGURACAO_STRINGS_CC',
            })
        if dc.get('protecao_cc_text'):
            items.append({
                'grupo': 'Proteção',
                'rotulo': 'Proteção CC (texto)',
                'valor': dc['protecao_cc_text'][:100] + '…' if len(dc['protecao_cc_text']) > 100 else dc['protecao_cc_text'],
                'token': 'PROTECAO_CC_DESCRICAO',
            })
        if dc.get('protecao_ca_text'):
            items.append({
                'grupo': 'Proteção',
                'rotulo': 'Proteção CA (texto)',
                'valor': dc['protecao_ca_text'][:100] + '…' if len(dc['protecao_ca_text']) > 100 else dc['protecao_ca_text'],
                'token': 'PROTECAO_CA_DESCRICAO',
            })
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

    bg = calc.get('breaker_groups') or {}
    if bg.get('total_breakers_detail'):
        items.append({
            'grupo': 'Proteção',
            'rotulo': 'Disjuntores CA (regra)',
            'valor': bg['total_breakers_detail'],
            'token': None,
        })
    for group in bg.get('breaker_groups') or []:
        items.append({
            'grupo': 'Proteção',
            'rotulo': f"Grupo {group.get('group_id', '?')} — {group.get('micros_count', '?')} micro(s)",
            'valor': (
                f"I={group.get('current_a', '—')} A → "
                f"disjuntor {group.get('breaker_a', '—')} A"
            ),
            'token': None,
        })

    if dc.get('cable_cc_note'):
        items.append({
            'grupo': 'Strings CC',
            'rotulo': 'Nota cabo CC',
            'valor': dc['cable_cc_note'],
            'token': None,
        })

    return items
