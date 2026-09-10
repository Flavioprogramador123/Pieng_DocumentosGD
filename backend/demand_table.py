"""
Geração de tabela de demanda (levantamento de carga) para memorial descritivo.
FD conforme NTC-04 Rev.4 CELG-D; cargas ajustadas para atingir a demanda-alvo informada.
"""

from __future__ import annotations

from typing import Any

from demand_table_fit import fit_loads_to_target
from equipment_enrichment import _query_specs, ai_available
from ntc04_demand_factors import apply_ntc04_to_loads

HEADERS = [
    'Item', 'Descrição', 'Pot. Unit. (W)', 'Qtd.', 'CI (kW)', 'FP',
    'CI (kVA)', 'FD', 'D (kW)', 'D (kVA)',
]

RESIDENTIAL_LOADS = [
    {'descricao': 'Iluminação residencial', 'tipo': 'iluminacao', 'pot_w': 100, 'qtd': 12, 'fp': 0.95},
    {'descricao': 'Tomadas de uso geral (TUG)', 'tipo': 'tug', 'pot_w': 100, 'qtd': 10, 'fp': 0.92},
    {'descricao': 'Chuveiro elétrico', 'tipo': 'chuveiro', 'pot_w': 5500, 'qtd': 1, 'fp': 1.00},
    {'descricao': 'Geladeira / freezer', 'tipo': 'geladeira', 'pot_w': 300, 'qtd': 1, 'fp': 0.85},
    {'descricao': 'Forno de micro-ondas', 'tipo': 'microondas', 'pot_w': 1000, 'qtd': 1, 'fp': 0.90},
    {'descricao': 'Ar-condicionado split', 'tipo': 'ar_condicionado', 'pot_w': 1200, 'qtd': 2, 'fp': 0.85},
]

REFERENCE_LOADS = [
    {'descricao': 'Iluminação industrial e circulação', 'tipo': 'iluminacao_tug', 'pot_w': 500, 'qtd': 4, 'fp': 0.95},
    {'descricao': 'Tomadas de uso geral e auxiliares', 'tipo': 'tug', 'pot_w': 750, 'qtd': 4, 'fp': 0.90},
    {'descricao': 'Compressor de ar industrial', 'tipo': 'motor', 'pot_w': 7500, 'qtd': 1, 'fp': 0.85},
    {'descricao': 'Bomba/motor de processo', 'tipo': 'motor', 'pot_w': 5500, 'qtd': 1, 'fp': 0.85},
    {'descricao': 'Motor de ventilação / exaustão industrial', 'tipo': 'motor', 'pot_w': 4500, 'qtd': 1, 'fp': 0.85},
    {'descricao': 'Impressoras e computadores', 'tipo': 'iluminacao_tug', 'pot_w': 2000, 'qtd': 1, 'fp': 0.95},
    {'descricao': 'Ar-condicionado comercial', 'tipo': 'ar_condicionado', 'pot_w': 3600, 'qtd': 2, 'fp': 0.85},
    {'descricao': 'Câmara fria / geladeira industrial', 'tipo': 'geladeira', 'pot_w': 800, 'qtd': 2, 'fp': 0.85},
    {'descricao': 'Esteira transportadora / motor de acionamento', 'tipo': 'motor', 'pot_w': 3000, 'qtd': 1, 'fp': 0.80},
    {'descricao': 'Iluminação de emergência e segurança', 'tipo': 'iluminacao', 'pot_w': 60, 'qtd': 8, 'fp': 0.95},
]


def _fmt_br(value: float, decimals: int = 2) -> str:
    return f'{value:.{decimals}f}'.replace('.', ',')


def _fmt_pct(fd: float) -> str:
    return f'{int(round(fd * 100))}%'


def _totals(rows: list[dict]) -> dict[str, float]:
    return {
        'ci_kw': round(sum(r['ci_kw'] for r in rows), 2),
        'ci_kva': round(sum(r['ci_kva'] for r in rows), 2),
        'd_kw': round(sum(r['d_kw'] for r in rows), 2),
        'd_kva': round(sum(r['d_kva'] for r in rows), 2),
    }


def _memorial_header(client_name: str, uc: str, classe: str, target_kw: float, d_kw: float, fit_note: str) -> str:
    """Memorial oficial: só a tabela — sem cabeçalho de demanda-alvo/cálculo."""
    return ''


def _rows_to_memorial_text(
    rows: list[dict],
    totals: dict[str, float],
    client_name: str,
    uc: str,
    classe: str,
    target_kw: float,
    source: str,
    fit_note: str,
) -> str:
    header = _memorial_header(client_name, uc, classe, target_kw, totals['d_kw'], fit_note)
    col_w = [4, 42, 12, 5, 8, 5, 8, 5, 8, 8]
    header_line = (
        f"{'Item':<{col_w[0]}} {'Descrição':<{col_w[1]}} {'Pot.W':>{col_w[2]}} "
        f"{'Qtd':>{col_w[3]}} {'CI kW':>{col_w[4]}} {'FP':>{col_w[5]}} "
        f"{'CI kVA':>{col_w[6]}} {'FD':>{col_w[7]}} {'D kW':>{col_w[8]}} {'D kVA':>{col_w[9]}}"
    )
    sep = '-' * len(header_line)
    body_lines = [header_line, sep] if not header.strip() else [header, header_line, sep]
    for row in rows:
        body_lines.append(
            f"{row['item']:<{col_w[0]}} {row['descricao'][:col_w[1]]:<{col_w[1]}} "
            f"{row['pot_unit_w']:>{col_w[2]}} {row['qtd']:>{col_w[3]}} "
            f"{_fmt_br(row['ci_kw']):>{col_w[4]}} {_fmt_br(row['fp']):>{col_w[5]}} "
            f"{_fmt_br(row['ci_kva']):>{col_w[6]}} {_fmt_pct(row['fd']):>{col_w[7]}} "
            f"{_fmt_br(row['d_kw']):>{col_w[8]}} {_fmt_br(row['d_kva']):>{col_w[9]}}"
        )
    body_lines.append(sep)
    body_lines.append(
        f"{'TOTAL':<{col_w[0]}} {'Demanda de projeto — conferir in loco':<{col_w[1]}} "
        f"{'—':>{col_w[2]}} {'—':>{col_w[3]}} "
        f"{_fmt_br(totals['ci_kw']):>{col_w[4]}} {'—':>{col_w[5]}} "
        f"{_fmt_br(totals['ci_kva']):>{col_w[6]}} {'—':>{col_w[7]}} "
        f"{_fmt_br(totals['d_kw']):>{col_w[8]}} {_fmt_br(totals['d_kva']):>{col_w[9]}}"
    )
    body_lines.append('')
    return '\n'.join(body_lines)


def _resolve_classe(classe: str, notes: str) -> str:
    notes_u = (notes or '').upper()
    if any(k in notes_u for k in ('RESID', 'RESIDÊNCIA', 'RESIDENCIA', 'CASA', 'DOMÉSTIC', 'DOMESTIC')):
        return 'RESIDENCIAL'
    if any(k in notes_u for k in ('INDUST', 'FÁBRICA', 'FABRICA')):
        return 'INDUSTRIAL'
    if any(k in notes_u for k in ('COMER', 'LOJA', 'ESCRITÓRIO', 'ESCRITORIO')):
        return 'COMERCIAL'
    base = (classe or '').strip().upper()
    if 'RESID' in base:
        return 'RESIDENCIAL'
    if 'IND' in base:
        return 'INDUSTRIAL'
    if 'COM' in base:
        return 'COMERCIAL'
    return classe.strip() if classe else 'RESIDENCIAL'


def _infer_tipo(descricao: str) -> str:
    d = (descricao or '').lower()
    if 'chuveiro' in d:
        return 'chuveiro'
    if 'micro' in d and 'ond' in d:
        return 'microondas'
    if 'condicionado' in d or 'split' in d:
        return 'ar_condicionado'
    if 'geladeira' in d or 'freezer' in d:
        return 'geladeira'
    if 'ilumin' in d or 'lâmpada' in d or 'lampada' in d:
        return 'iluminacao'
    if 'tomada' in d or 'tug' in d:
        return 'tug'
    if 'secadora' in d:
        return 'secadora'
    if 'compressor' in d or 'motor' in d or 'bomba' in d:
        return 'motor'
    return 'outro'


def _normalize_load(row: dict) -> dict:
    desc = row.get('descricao') or row.get('description') or 'Carga'
    tipo = (row.get('tipo') or row.get('kind') or _infer_tipo(desc)).lower()
    return {
        'descricao': desc,
        'tipo': tipo,
        'pot_w': float(row.get('pot_w') or row.get('potencia_w') or 1000),
        'qtd': int(float(row.get('qtd') or row.get('quantidade') or 1)),
        'fp': float(row.get('fp') or row.get('fator_potencia') or 0.92),
    }


def _ai_demand_prompt(target_kw: float, classe: str, client_name: str, uc: str, notes: str) -> str:
    from normas_enrichment import ai_demand_prompt_suffix

    normas_ctx = ai_demand_prompt_suffix()
    return f"""Monte um levantamento de carga elétrica para memorial (Equatorial Goiás / NTC-04).
Classe: {classe}
Demanda-alvo: {target_kw} kW
Cliente: {client_name or 'não informado'}
UC: {uc or 'não informada'}
Contexto: {notes or 'nenhum'}

{normas_ctx}

REGRAS: não informe fd (calculado pela NTC-04). Composição plausível para ~{target_kw} kW.

Retorne APENAS JSON:
{{"rows": [{{"descricao": "Chuveiro elétrico", "tipo": "chuveiro", "pot_w": 5500, "qtd": 1, "fp": 1.0}}]}}
tipos: iluminacao, tug, chuveiro, microondas, ar_condicionado, geladeira, secadora, motor."""


def _loads_from_ai(target_kw: float, classe: str, client_name: str, uc: str, notes: str):
    specs, source = _query_specs(_ai_demand_prompt(target_kw, classe, client_name, uc, notes))
    if not specs or 'rows' not in specs:
        return None, 'none'
    loads = [_normalize_load(row) for row in specs['rows'] if row.get('descricao')]
    if not loads:
        return None, 'none'
    return loads, source


def generate_demand_table(
    target_kw: float,
    classe: str = 'RESIDENCIAL',
    client_name: str = '',
    uc: str = '',
    notes: str = '',
    prefer_ai: bool = False,
    base_loads: list[dict] | None = None,
    modelo_id: str | None = None,
) -> dict[str, Any]:
    """Gera tabela ajustada à demanda-alvo com FD conforme NTC-04."""
    target_kw = float(target_kw)
    if target_kw <= 0:
        raise ValueError('Demanda-alvo deve ser maior que zero')

    classe = _resolve_classe(classe, notes)
    source = 'ntc04'

    if base_loads is None and modelo_id:
        from demand_presets import get_model, model_base_loads
        preset = get_model(modelo_id)
        if preset:
            base_loads = model_base_loads(preset)
            if not notes:
                notes = preset.get('notas') or ''
            if classe == 'RESIDENCIAL' and preset.get('classe'):
                classe = _resolve_classe(preset.get('classe'), notes)

    if base_loads is None and prefer_ai and ai_available():
        ai_loads, ai_source = _loads_from_ai(target_kw, classe, client_name, uc, notes)
        if ai_loads:
            base_loads = ai_loads
            source = f'ai+ntc04:{ai_source}'

    if base_loads is None:
        base_loads = RESIDENTIAL_LOADS if 'RESID' in classe.upper() else REFERENCE_LOADS
        source = 'ntc04:template'
    elif modelo_id:
        source = f'ntc04:modelo:{modelo_id}'
    else:
        source = 'ntc04:custom'

    rows, calculated_d, fit_note = fit_loads_to_target(base_loads, target_kw, classe)
    totals = _totals(rows)
    memorial_text = _rows_to_memorial_text(
        rows, totals, client_name, uc, classe, target_kw, source, fit_note,
    )

    return {
        'target_kw': target_kw,
        'classe': classe,
        'client_name': client_name,
        'uc': uc,
        'headers': HEADERS,
        'rows': rows,
        'totals': totals,
        'calculated_d_kw': calculated_d,
        'fit_note': fit_note,
        'memorial_text': memorial_text,
        'source': source,
        'disclaimer': (
            'FD conforme NTC-04 Rev.4 CELG-D. Cargas ajustadas à demanda-alvo informada; '
            'conferir potências e quantidades reais antes do protocolo.'
        ),
    }
