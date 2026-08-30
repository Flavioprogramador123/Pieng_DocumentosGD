"""
Enriquece payload normalizado antes da geração TXT/tokens.
Preenche specs do catálogo SQLite, defaults de engenharia e tabela de demanda.
"""

from __future__ import annotations

import json
from typing import Any

from catalog_db import (
    catalog_inverter_to_specs,
    catalog_module_to_specs,
    find_inverter_by_name_or_power,
    find_module_by_name_or_power,
    lookup_padrao,
)

MODULE_SPEC_KEYS = ('potencia', 'voc', 'isc', 'vmpp', 'impp', 'eficiencia')
INVERTER_SPEC_KEYS = (
    'potencia', 'tipo_inversor', 'num_mppt', 'mppt_min', 'mppt_max',
    'tensao_nominal', 'corrente_nominal', 'eficiencia',
    'corrente_max_cc', 'tensao_max_cc', 'potencia_max_cc_kw',
    'potencia_max_saida_ca_kw', 'corrente_max_saida_ca',
    'tensao_min_ca', 'tensao_max_ca', 'thd_pct', 'fator_potencia',
    'frequencia_hz', 'tensao_partida_cc', 'qtd_strings_max',
)
MODULE_DIM_KEYS = ('comprimento_m', 'largura_m', 'peso_kg')


def _empty(val: Any) -> bool:
    return val is None or str(val).strip() == ''


def _fill_module_from_catalog(module: dict) -> None:
    """
    Preenche especificações de módulo a partir do catálogo SQLite.
    Match exato apenas — não usa specs de outra potência.
    """
    fab = (module.get('fabricante') or '').strip()
    mod = (module.get('modelo') or module.get('model') or '').strip()
    pot = module.get('potencia') or module.get('power') or 0

    if not fab and not mod:
        return

    # Busca inteligente: 3 camadas (exato → potência → tolerância)
    row = find_module_by_name_or_power(
        fabricante=fab,
        modelo=mod,
        potencia_wp=pot,
    )

    if not row:
        return

    # Preencher fabricante e modelo (caso usuário tenha digitado parcialmente)
    module.setdefault('fabricante', row.get('fabricante'))
    module.setdefault('modelo', row.get('modelo'))

    # Preencher especificações técnicas
    specs = catalog_module_to_specs(row)
    for key in MODULE_SPEC_KEYS:
        if _empty(module.get(key)) and specs.get(key) is not None:
            module[key] = specs[key]

    # Preencher dimensões
    for key in MODULE_DIM_KEYS:
        if _empty(module.get(key)) and row.get(key) is not None:
            module[key] = row[key]

    # Calcular área do módulo
    if _empty(module.get('area_modulo')) and row.get('comprimento_m') and row.get('largura_m'):
        try:
            module['area_modulo'] = round(float(row['comprimento_m']) * float(row['largura_m']), 3)
        except (TypeError, ValueError):
            pass


def _fill_inverter_from_catalog(inverter: dict) -> None:
    """
    Preenche especificações de inversor a partir do catálogo SQLite.
    Usa busca inteligente de 3 camadas (exato → potência → tolerância ±10%).

    IMPORTANTE: Preenche TODOS os campos técnicos, incluindo num_mppt!
    """
    fab = (inverter.get('fabricante') or '').strip()
    mod = (inverter.get('modelo') or inverter.get('model') or '').strip()
    pot = inverter.get('potencia') or inverter.get('power') or 0

    if not fab and not mod:
        return

    # Busca inteligente: 3 camadas (exato → potência → tolerância)
    row = find_inverter_by_name_or_power(
        fabricante=fab,
        modelo=mod,
        potencia_kw=pot,
    )

    if not row:
        return

    # Preencher fabricante e modelo (caso usuário tenha digitado parcialmente)
    inverter.setdefault('fabricante', row.get('fabricante'))
    inverter.setdefault('modelo', row.get('modelo'))

    # Preencher especificações técnicas (incluindo num_mppt!)
    specs = catalog_inverter_to_specs(row)
    for key in INVERTER_SPEC_KEYS:
        if _empty(inverter.get(key)) and specs.get(key) is not None:
            inverter[key] = specs[key]

    # Preencher campos adicionais diretamente do row (redundância para garantir)
    for key in INVERTER_SPEC_KEYS:
        if _empty(inverter.get(key)) and row.get(key) is not None:
            inverter[key] = row[key]


def _apply_padrao_entrada(normalized: dict) -> None:
    from normas_loader import apply_normas_to_payload, load_normas

    if load_normas():
        apply_normas_to_payload(normalized)
        return

    cliente = normalized.get('cliente') or {}
    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})
    uf = (cliente.get('uf') or 'GO').upper()[:2]
    tipo = (uc.get('tipo_ligacao') or 'MONOFASICO').upper()
    padrao = lookup_padrao(uf, tipo)
    if not padrao:
        return
    if _empty(uc.get('disjuntor_entrada')) and padrao.get('disjuntor_a'):
        uc['disjuntor_entrada'] = str(padrao['disjuntor_a'])
    if _empty(uc.get('tensao_atendimento')) and padrao.get('tensao_v'):
        uc['tensao_atendimento'] = padrao['tensao_v']
    if _empty(tec.get('bitola_cabo_padrao')) and padrao.get('bitola_cabo_mm2'):
        tec['bitola_cabo_padrao'] = padrao['bitola_cabo_mm2']
    if _empty(tec.get('dps_tipo')) and padrao.get('dps_tipo'):
        tec['dps_tipo'] = padrao['dps_tipo']
        tec.setdefault('dps_cc', padrao['dps_tipo'])
    if _empty(tec.get('disjuntor_curva')) and padrao.get('curva_disjuntor'):
        tec['disjuntor_curva'] = padrao['curva_disjuntor']
    if _empty(tec.get('dr_sensibilidade_ma')) and padrao.get('dr_ma'):
        tec['dr_sensibilidade_ma'] = str(padrao['dr_ma'])


def _apply_engineering_defaults(normalized: dict) -> None:
    """Defaults técnicos buscáveis / norma residencial — reduzem NULL no memorial."""
    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})
    tipo = (uc.get('tipo_ligacao') or 'MONOFASICO').upper()
    from grid_voltage import resolve_ligacao_config
    lig = resolve_ligacao_config(tipo)
    tec.setdefault('tipo_fonte', 'SOLAR FOTOVOLTAICA')
    uc.setdefault('modalidade_compensacao', 'AUTOCONSUMO LOCAL')
    tec.setdefault('armazenamento', 'NÃO')

    # Disjuntor geral de CA (padrão de entrada)
    tec.setdefault('disjuntor_polos', lig['num_polos_disjuntor'])
    tec.setdefault('disjuntor_tensao_nominal', uc.get('tensao_atendimento', '220V').replace('V', ''))
    tec.setdefault('disjuntor_corrente_nominal', uc.get('disjuntor_entrada', '40'))
    tec.setdefault('disjuntor_frequencia', '60')
    tec.setdefault('disjuntor_capacidade_ka', '10')
    tec.setdefault('disjuntor_curva', tec.get('disjuntor_curva') or 'C')
    tec.setdefault('disjuntor_elemento', 'Termomagnético')
    tec.setdefault('disjuntor_acionamento', 'Manual')

    # DPS
    tec.setdefault('dps_tipo', tec.get('dps_cc') or 'DPS Classe II')
    tec.setdefault('dps_classe', tec.get('dps_ca') or '275 V')
    tec.setdefault('dps_tensao_v', '275')
    tec.setdefault('dps_corrente_nominal_ka', '5')
    tec.setdefault('dps_corrente_maxima_ka', '10')

    tec.setdefault('bitola_cabo_cc', '4 mm²')
    tec.setdefault('bitola_cabo_ca', '6 mm²')
    tec.setdefault('bitola_cabo_padrao', '10 mm²')

    for mod in normalized.get('modulos') or []:
        if _empty(mod.get('area_modulo')):
            if mod.get('comprimento_m') and mod.get('largura_m'):
                try:
                    mod['area_modulo'] = round(
                        float(mod['comprimento_m']) * float(mod['largura_m']), 3
                    )
                except (TypeError, ValueError):
                    mod['area_modulo'] = 2.5
            else:
                mod['area_modulo'] = 2.5
    modulos = normalized.get('modulos') or []
    if modulos and _empty(tec.get('area_arranjo')):
        try:
            total_q = sum(int(m.get('quantidade') or 0) for m in modulos)
            area_u = float(modulos[0].get('area_modulo') or 2.5)
            if total_q > 0:
                tec['area_arranjo'] = round(total_q * area_u, 3)
        except (TypeError, ValueError):
            pass

    # Inversor — defaults quando catálogo não tem
    for inv in normalized.get('inversores') or []:
        inv.setdefault('fator_potencia', '0,99')
        inv.setdefault('thd_pct', '3')
        inv.setdefault('frequencia_hz', '60')
        inv.setdefault('tensao_min_ca', '180')
        inv.setdefault('tensao_max_ca', '270')
        if inv.get('mppt_min') and inv.get('mppt_max') and _empty(inv.get('faixa_tensao_mppt')):
            inv['faixa_tensao_mppt'] = f"{inv['mppt_min']} - {inv['mppt_max']}"
        if inv.get('potencia') and _empty(inv.get('potencia_nominal_ca_kw')):
            inv['potencia_nominal_ca_kw'] = inv['potencia']
        if inv.get('potencia') and _empty(inv.get('potencia_max_saida_ca_kw')):
            try:
                inv['potencia_max_saida_ca_kw'] = round(float(inv['potencia']) * 1.1, 2)
            except (TypeError, ValueError):
                pass
        if inv.get('num_mppt') and _empty(inv.get('qtd_entradas_mppt')):
            inv['qtd_entradas_mppt'] = inv['num_mppt']
        if inv.get('mppt_min') and _empty(inv.get('tensao_partida_cc')):
            inv['tensao_partida_cc'] = inv['mppt_min']

    tec.setdefault('fator_potencia', '0,92')


def _resolve_coordinates(normalized: dict) -> None:
    from coordinate_utils import enrich_normalized_coordinates
    enrich_normalized_coordinates(normalized)


def _ensure_demand_table(normalized: dict) -> None:
    tec = normalized.setdefault('dados_tecnicos', {})
    if not _empty(tec.get('tabela_demanda_json')):
        return
    alvo = tec.get('demanda_alvo_kw')
    modelo_id = tec.get('demanda_modelo_id')
    if _empty(alvo) and not modelo_id:
        return
    try:
        cliente = normalized.get('cliente') or {}
        uc = normalized.get('unidade_consumidora') or {}
        if modelo_id:
            from demand_presets import generate_from_model
            table = generate_from_model(
                modelo_id,
                client_name=cliente.get('nome') or '',
                uc=uc.get('numero') or '',
                target_kw=float(str(alvo).replace(',', '.')) if not _empty(alvo) else None,
                notes=tec.get('demanda_notas') or '',
            )
        else:
            from demand_table import generate_demand_table
            table = generate_demand_table(
                target_kw=float(str(alvo).replace(',', '.')),
                classe=uc.get('classe') or 'RESIDENCIAL',
                client_name=cliente.get('nome') or '',
                uc=uc.get('numero') or '',
                notes=tec.get('demanda_notas') or '',
            )
        tec['tabela_demanda_text'] = table.get('memorial_text') or ''
        tec['tabela_demanda_json'] = json.dumps(table, ensure_ascii=False)
    except Exception:
        pass


def enrich_normalized_payload(normalized: dict) -> dict:
    """Pipeline único antes de create_txt_data / gerar_documentos."""
    from normas_enrichment import apply_normas_enrichment

    result = dict(normalized or {})
    result['cliente'] = dict(result.get('cliente') or {})
    result['unidade_consumidora'] = dict(result.get('unidade_consumidora') or {})
    result['dados_tecnicos'] = dict(result.get('dados_tecnicos') or {})
    result['modulos'] = [dict(m) for m in (result.get('modulos') or []) if m]
    result['inversores'] = [dict(i) for i in (result.get('inversores') or []) if i]

    for mod in result['modulos']:
        _fill_module_from_catalog(mod)
    for inv in result['inversores']:
        _fill_inverter_from_catalog(inv)
    apply_normas_enrichment(result)
    _apply_engineering_defaults(result)
    _resolve_coordinates(result)
    _ensure_demand_table(result)
    return result
