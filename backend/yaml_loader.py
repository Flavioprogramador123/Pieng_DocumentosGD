"""
Importação e exportação YAML — mesmo schema de tokens do formulário/TXT.
Enriquece dados faltantes via catálogo SQLite antes de popular o frontend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog_db import (
    catalog_inverter_to_specs,
    catalog_module_to_specs,
    lookup_inverter,
    lookup_module,
    lookup_padrao,
)
from form_mapper import normalize_form_payload
from residential_defaults import apply_residential_defaults

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / 'dados' / 'projeto_padrao.yaml'


def _s(val: Any) -> str:
    if val is None:
        return ''
    return str(val).strip()


def parse_yaml_content(text: str) -> dict:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError('O YAML deve ser um objeto na raiz (cliente:, modulos:, ...)')
    return data


def enrich_from_catalog(normalized: dict) -> tuple[dict, list[str]]:
    """Preenche lacunas a partir do catálogo SQLite. Retorna (dados, mensagens)."""
    notes: list[str] = []
    cliente = normalized.setdefault('cliente', {})
    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})

    uf = _s(cliente.get('uf')) or 'GO'
    tipo = _s(uc.get('tipo_ligacao')).upper() or 'MONOFASICO'
    padrao = lookup_padrao(uf, tipo)
    if padrao:
        if not uc.get('disjuntor_entrada') and padrao.get('disjuntor_a'):
            uc['disjuntor_entrada'] = padrao['disjuntor_a']
            notes.append(f'Padrão {uf}/{tipo}: disjuntor {padrao["disjuntor_a"]} A')
        if not uc.get('tensao_atendimento') and padrao.get('tensao_v'):
            uc['tensao_atendimento'] = padrao['tensao_v']
        if not tec.get('bitola_cabo_padrao') and padrao.get('bitola_cabo_mm2'):
            tec['bitola_cabo_padrao'] = padrao['bitola_cabo_mm2']
        if not tec.get('dps_cc') and padrao.get('dps_tipo'):
            tec['dps_cc'] = padrao['dps_tipo']
            tec.setdefault('dps_tipo', padrao['dps_tipo'])
        if not tec.get('disjuntor_curva') and padrao.get('curva_disjuntor'):
            tec['disjuntor_curva'] = padrao['curva_disjuntor']
        if not tec.get('dr_sensibilidade_ma') and padrao.get('dr_ma'):
            tec['dr_sensibilidade_ma'] = padrao['dr_ma']

    for m in normalized.get('modulos') or []:
        fab, mod = _s(m.get('fabricante')), _s(m.get('modelo'))
        if not fab and not mod:
            continue
        missing = not any(m.get(k) for k in ('voc', 'isc', 'vmpp', 'impp', 'potencia'))
        if missing:
            row = lookup_module(fab, mod)
            if row:
                for k, v in catalog_module_to_specs(row).items():
                    if v is not None and not m.get(k):
                        m[k] = v
                notes.append(f'Módulo catálogo: {row["fabricante"]} {row["modelo"]}')

    for inv in normalized.get('inversores') or []:
        fab, mod = _s(inv.get('fabricante')), _s(inv.get('modelo'))
        if not fab and not mod:
            continue
        missing = not any(inv.get(k) for k in ('mppt_min', 'mppt_max', 'potencia', 'corrente_nominal'))
        if missing:
            row = lookup_inverter(fab, mod)
            if row:
                for k, v in catalog_inverter_to_specs(row).items():
                    if v is not None and not inv.get(k):
                        inv[k] = v
                if row.get('tipo_inversor') and not inv.get('tipo_inversor'):
                    inv['tipo_inversor'] = row['tipo_inversor']
                if row.get('num_mppt') and not inv.get('num_mppt'):
                    inv['num_mppt'] = row['num_mppt']
                notes.append(f'Inversor catálogo: {row["fabricante"]} {row["modelo"]}')

    return normalized, notes


def normalized_to_frontend(normalized: dict) -> dict:
    """Converte estrutura aninhada para o formato de applyLocalParse (App.jsx)."""
    c = normalized.get('cliente') or {}
    uc = normalized.get('unidade_consumidora') or {}
    t = normalized.get('dados_tecnicos') or {}

    client = {
        'client_name': _s(c.get('nome')),
        'cpf': _s(c.get('cpf')),
        'rg': _s(c.get('rg')),
        'data_nascimento': _s(c.get('data_nascimento')),
        'validade_cnh': _s(c.get('validade_cnh')),
        'logradouro': _s(c.get('logradouro')),
        'numero': _s(c.get('numero')),
        'complemento': _s(c.get('complemento')),
        'bairro': _s(c.get('bairro')),
        'cidade': _s(c.get('cidade')),
        'uf': _s(c.get('uf')),
        'cep': _s(c.get('cep')),
        'telefone': _s(c.get('telefone')),
        'email': _s(c.get('email')),
        'consumer_unit': _s(uc.get('numero')),
        'tensao_atendimento': _s(uc.get('tensao_atendimento')),
        'tipo_ligacao': _s(uc.get('tipo_ligacao')),
        'classe': _s(uc.get('classe')),
    }

    technical = {
        'disjuntor_entrada': _s(uc.get('disjuntor_entrada') or t.get('disjuntor_entrada')),
        'curva_disjuntor': _s(t.get('disjuntor_curva') or t.get('curva_disjuntor')),
        'dps_tipo': _s(t.get('dps_tipo') or t.get('dps_cc')),
        'dps_classe': _s(t.get('dps_ca') or t.get('dps_classe')),
        'bitola_cabo_ca': _s(t.get('bitola_cabo_ca')),
        'bitola_cabo_cc': _s(t.get('bitola_cabo_cc')),
        'bitola_cabo_padrao': _s(t.get('bitola_cabo_padrao')),
        'tipo_aterramento': _s(t.get('tipo_aterramento')),
        'resistencia_aterramento': _s(t.get('resistencia_aterramento')),
        'aterramento': _s(t.get('aterramento')),
        'fuso_utm': _s(t.get('fuso_utm')),
        'tipo_arranjo': _s(t.get('tipo_arranjo')),
        'tipo_fonte': _s(t.get('tipo_fonte')),
        'dr_sensibilidade_ma': _s(t.get('dr_sensibilidade_ma')),
        'dr_tipo': _s(t.get('dr_tipo')),
        'data_documento': _s(t.get('data_documento')),
        'data_operacao': _s(t.get('data_operacao')),
        'coordenada_utm_x': _s(uc.get('coordenada_utm_x') or t.get('coordenada_utm_x')),
        'coordenada_utm_y': _s(uc.get('coordenada_utm_y') or t.get('coordenada_utm_y')),
        'latitude': _s(t.get('latitude')),
        'longitude': _s(t.get('longitude')),
        'num_poste': _s(uc.get('num_poste') or t.get('num_poste')),
        'area_arranjo': _s(t.get('area_arranjo')),
        'demanda_alvo_kw': _s(t.get('demanda_alvo_kw')),
        'demanda_notas': _s(t.get('demanda_notas')),
        'tabela_demanda_text': _s(t.get('tabela_demanda_text')),
        'modulos_por_string': _s(t.get('modulos_por_string')),
        'num_mppt': _s(t.get('num_mppt')),
        'tipo_inversor': _s(t.get('tipo_inversor')),
    }

    modules = []
    for m in normalized.get('modulos') or []:
        modules.append({
            'quantity': _s(m.get('quantidade')),
            'fabricante': _s(m.get('fabricante')),
            'model': _s(m.get('modelo')),
            'power': _s(m.get('potencia')),
            'voc': _s(m.get('voc')),
            'isc': _s(m.get('isc')),
            'vmpp': _s(m.get('vmpp')),
            'impp': _s(m.get('impp')),
            'eficiencia': _s(m.get('eficiencia')),
        })

    inverters = []
    for inv in normalized.get('inversores') or []:
        inverters.append({
            'quantity': _s(inv.get('quantidade')),
            'fabricante': _s(inv.get('fabricante')),
            'model': _s(inv.get('modelo')),
            'power': _s(inv.get('potencia')),
            'tensao_nominal': _s(inv.get('tensao_nominal')),
            'corrente_nominal': _s(inv.get('corrente_nominal')),
            'mppt_min': _s(inv.get('mppt_min')),
            'mppt_max': _s(inv.get('mppt_max')),
            'eficiencia': _s(inv.get('eficiencia')),
        })

    if not modules:
        modules = [{'quantity': '', 'fabricante': '', 'model': '', 'power': '',
                    'voc': '', 'isc': '', 'vmpp': '', 'impp': '', 'eficiencia': ''}]
    if not inverters:
        inverters = [{'quantity': '', 'fabricante': '', 'model': '', 'power': '',
                      'tensao_nominal': '', 'corrente_nominal': '', 'mppt_min': '',
                      'mppt_max': '', 'eficiencia': ''}]

    return {'client': client, 'technical': technical, 'modules': modules, 'inverters': inverters}


def import_yaml_project(text: str) -> dict:
    raw = parse_yaml_content(text)
    normalized = normalize_form_payload(raw)
    from token_enrichment import enrich_normalized_payload
    normalized = enrich_normalized_payload(normalized)
    from residential_defaults import apply_residential_defaults
    normalized = apply_residential_defaults(normalized)
    parsed = normalized_to_frontend(normalized)
    catalog_notes: list[str] = []
    for m in normalized.get('modulos') or []:
        if m.get('voc'):
            catalog_notes.append(f"Módulo {m.get('fabricante')} {m.get('modelo')}: specs OK")
            break
    return {
        'success': True,
        'normalized': normalized,
        'parsed': parsed,
        'catalog_notes': catalog_notes,
    }


def export_form_to_yaml(data: dict) -> str:
    normalized = normalize_form_payload(data)
    export = {
        'versao': '1.0',
        'cliente': normalized.get('cliente') or {},
        'unidade_consumidora': normalized.get('unidade_consumidora') or {},
        'dados_tecnicos': normalized.get('dados_tecnicos') or {},
        'modulos': normalized.get('modulos') or [],
        'inversores': normalized.get('inversores') or [],
    }
    return yaml.dump(
        export,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )


def read_template() -> str:
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f'Template não encontrado: {TEMPLATE_PATH}')
    return TEMPLATE_PATH.read_text(encoding='utf-8')
