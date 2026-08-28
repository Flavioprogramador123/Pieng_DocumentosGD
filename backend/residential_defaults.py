"""
Valores padrão para instalações residenciais comuns (só preenchem campos vazios).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


RESIDENTIAL_TECHNICAL_DEFAULTS = {
    'tipo_aterramento': 'Haste copper 2,4 m com caixa de inspeção',
    'resistencia_aterramento': '≤ 10 Ω',
    'bitola_cabo_cc': '6 mm²',
    'bitola_cabo_ca': '10 mm²',
    'bitola_cabo_padrao': '10 mm²',
    'curva_disjuntor': 'C',
    'dps_tipo': 'DPS Classe II',
    'dps_classe': '275 V',
    'fuso_utm': '22S',
    'tipo_fonte': 'SOLAR FOTOVOLTAICA',
    'tipo_arranjo': 'Telhado inclinado',
    'dr_sensibilidade_ma': '30',
    'dr_tipo': 'DR 30 mA — alta sensibilidade',
}

RESIDENTIAL_UC_DEFAULTS = {
    'tipo_ligacao': 'MONOFASICO',
    'tensao_atendimento': '220V',
    'classe': 'RESIDENCIAL',
    'disjuntor_entrada': '40',
    'fuso_utm': '22S',
}


def today_iso() -> str:
    return date.today().isoformat()


def today_br() -> str:
    return datetime.now().strftime('%d/%m/%Y')


def iso_to_br(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if re_match_iso(text):
        y, m, d = text.split('-')
        return f'{d}/{m}/{y}'
    return text


def re_match_iso(text: str) -> bool:
    import re
    return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', text))


def _is_empty(val: Any) -> bool:
    return val is None or str(val).strip() == ''


def apply_residential_defaults(payload: dict) -> dict:
    """
    Preenche lacunas em payload normalizado (cliente, uc, dados_tecnicos).
    Nunca sobrescreve valor já informado pelo usuário.
    """
    result = dict(payload or {})
    result['cliente'] = dict(result.get('cliente') or {})
    result['unidade_consumidora'] = dict(result.get('unidade_consumidora') or {})
    result['dados_tecnicos'] = dict(result.get('dados_tecnicos') or {})
    result.setdefault('modulos', list(payload.get('modulos') or []))
    result.setdefault('inversores', list(payload.get('inversores') or []))

    classe = (
        result['unidade_consumidora'].get('classe')
        or result['cliente'].get('classe')
        or 'RESIDENCIAL'
    ).upper()
    is_residential = 'RESID' in classe or 'COMER' not in classe and 'IND' not in classe

    if is_residential:
        for key, val in RESIDENTIAL_UC_DEFAULTS.items():
            if _is_empty(result['unidade_consumidora'].get(key)):
                result['unidade_consumidora'][key] = val

        for key, val in RESIDENTIAL_TECHNICAL_DEFAULTS.items():
            if _is_empty(result['dados_tecnicos'].get(key)):
                result['dados_tecnicos'][key] = val

        try:
            from catalog_db import lookup_padrao
            padrao = lookup_padrao(
                result['cliente'].get('uf'),
                result['unidade_consumidora'].get('tipo_ligacao'),
            )
            if padrao:
                uc = result['unidade_consumidora']
                dt = result['dados_tecnicos']
                if _is_empty(uc.get('disjuntor_entrada')) and padrao.get('disjuntor_a'):
                    uc['disjuntor_entrada'] = str(padrao['disjuntor_a'])
                if _is_empty(dt.get('bitola_cabo_padrao')) and padrao.get('bitola_cabo_mm2'):
                    dt['bitola_cabo_padrao'] = padrao['bitola_cabo_mm2']
                if _is_empty(dt.get('dps_tipo')) and padrao.get('dps_tipo'):
                    dt['dps_tipo'] = padrao['dps_tipo']
                if _is_empty(dt.get('curva_disjuntor')) and padrao.get('curva_disjuntor'):
                    dt['curva_disjuntor'] = padrao['curva_disjuntor']
                if _is_empty(dt.get('dr_sensibilidade_ma')) and padrao.get('dr_ma'):
                    dt['dr_sensibilidade_ma'] = str(padrao['dr_ma'])
                if _is_empty(result['unidade_consumidora'].get('tensao_atendimento')) and padrao.get('tensao_v'):
                    uc['tensao_atendimento'] = padrao['tensao_v']
        except Exception:
            pass

        if (
            _is_empty(result['dados_tecnicos'].get('aterramento'))
            and result['dados_tecnicos'].get('tipo_aterramento')
        ):
            tipo = result['dados_tecnicos']['tipo_aterramento']
            res = result['dados_tecnicos'].get('resistencia_aterramento', '')
            result['dados_tecnicos']['aterramento'] = f'{tipo} — {res}'.strip(' —')

    # Data do documento / operação → hoje se vazio
    doc_date = (
        result['dados_tecnicos'].get('data_documento')
        or result['cliente'].get('data_documento')
    )
    if _is_empty(doc_date):
        doc_date = today_iso()
        result['dados_tecnicos']['data_documento'] = doc_date

    if _is_empty(result['dados_tecnicos'].get('data_operacao')):
        result['dados_tecnicos']['data_operacao'] = doc_date

    return result
