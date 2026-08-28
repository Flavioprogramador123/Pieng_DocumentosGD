"""
Geração de tabela de demanda (levantamento de carga) para memorial descritivo.
Escala modelo de referência industrial (~20 kW) ou usa IA quando disponível.
"""

from __future__ import annotations

import json
import re
from typing import Any

from equipment_enrichment import _extract_json, _query_specs, ai_available

HEADERS = [
    'Item', 'Descrição', 'Pot. Unit. (W)', 'Qtd.', 'CI (kW)', 'FP',
    'CI (kVA)', 'FD', 'D (kW)', 'D (kVA)',
]

# Modelo de referência (~20 kW de demanda) — conferir no local antes do protocolo
REFERENCE_LOADS = [
    {'descricao': 'Iluminação industrial e áreas de circulação', 'pot_w': 500, 'qtd': 4, 'fp': 0.95, 'fd': 1.00},
    {'descricao': 'Tomadas de uso geral e equipamentos auxiliares', 'pot_w': 750, 'qtd': 4, 'fp': 0.90, 'fd': 0.80},
    {'descricao': 'Compressor de ar industrial', 'pot_w': 7500, 'qtd': 1, 'fp': 0.85, 'fd': 0.80},
    {'descricao': 'Bomba/motor de processo', 'pot_w': 5500, 'qtd': 1, 'fp': 0.85, 'fd': 0.80},
    {'descricao': 'Máquina de solda / equipamento de produção', 'pot_w': 5000, 'qtd': 1, 'fp': 0.80, 'fd': 0.80},
    {'descricao': 'Escritório, informática e apoio', 'pot_w': 2000, 'qtd': 1, 'fp': 0.95, 'fd': 0.60},
]

RESIDENTIAL_LOADS = [
    {'descricao': 'Iluminação residencial', 'pot_w': 100, 'qtd': 12, 'fp': 0.95, 'fd': 0.70},
    {'descricao': 'Tomadas de uso geral', 'pot_w': 100, 'qtd': 10, 'fp': 0.92, 'fd': 0.40},
    {'descricao': 'Geladeira / freezer', 'pot_w': 300, 'qtd': 2, 'fp': 0.85, 'fd': 0.80},
    {'descricao': 'Micro-ondas e eletrodomésticos', 'pot_w': 1500, 'qtd': 1, 'fp': 0.90, 'fd': 0.60},
    {'descricao': 'Ar-condicionado split', 'pot_w': 1200, 'qtd': 2, 'fp': 0.85, 'fd': 0.70},
    {'descricao': 'Chuveiro elétrico', 'pot_w': 5500, 'qtd': 1, 'fp': 1.00, 'fd': 0.40},
]


def _compute_row(item: int, load: dict[str, Any]) -> dict[str, Any]:
    pot_w = float(load['pot_w'])
    qtd = float(load['qtd'])
    fp = float(load['fp'])
    fd = float(load['fd'])
    ci_kw = pot_w * qtd / 1000
    ci_kva = ci_kw / fp if fp else ci_kw
    d_kw = ci_kw * fd
    d_kva = ci_kva * fd
    return {
        'item': str(item),
        'descricao': load['descricao'],
        'pot_unit_w': int(pot_w),
        'qtd': int(qtd),
        'ci_kw': round(ci_kw, 2),
        'fp': fp,
        'ci_kva': round(ci_kva, 2),
        'fd': fd,
        'd_kw': round(d_kw, 2),
        'd_kva': round(d_kva, 2),
    }


def _fmt_br(value: float, decimals: int = 2) -> str:
    text = f'{value:.{decimals}f}'.replace('.', ',')
    if decimals == 0:
        return text
    return text


def _fmt_pct(fd: float) -> str:
    return f'{int(round(fd * 100))}%'


def _rows_from_loads(loads: list[dict]) -> list[dict]:
    return [_compute_row(i + 1, load) for i, load in enumerate(loads)]


def _totals(rows: list[dict]) -> dict[str, float]:
    return {
        'ci_kw': round(sum(r['ci_kw'] for r in rows), 2),
        'ci_kva': round(sum(r['ci_kva'] for r in rows), 2),
        'd_kw': round(sum(r['d_kw'] for r in rows), 2),
        'd_kva': round(sum(r['d_kva'] for r in rows), 2),
    }


def _scale_rows_to_target(rows: list[dict], target_kw: float) -> list[dict]:
    total = _totals(rows)['d_kw']
    if total <= 0:
        return rows
    factor = target_kw / total
    scaled = []
    for row in rows:
        scaled.append({
            **row,
            'd_kw': round(row['d_kw'] * factor, 2),
            'd_kva': round(row['d_kva'] * factor, 2),
        })
    return scaled


def _memorial_header(client_name: str, uc: str, classe: str, target_kw: float) -> str:
    """Corpo da tabela (título 'Tabela 1' fica no template Word)."""
    lines = [
        f'Demanda-alvo de referência: {_fmt_br(target_kw)} kW',
    ]
    meta = []
    if client_name:
        meta.append(f'Cliente: {client_name}')
    if uc:
        meta.append(f'UC: {uc}')
    if classe:
        meta.append(f'Classe: {classe}')
    if meta:
        lines.append(' | '.join(meta))
    lines.append('')
    return '\n'.join(lines)


def _rows_to_memorial_text(
    rows: list[dict],
    totals: dict[str, float],
    client_name: str,
    uc: str,
    classe: str,
    target_kw: float,
    source: str,
) -> str:
    header = _memorial_header(client_name, uc, classe, target_kw)
    col_w = [4, 42, 12, 5, 8, 5, 8, 5, 8, 8]
    header_line = (
        f"{'Item':<{col_w[0]}} {'Descrição':<{col_w[1]}} {'Pot.W':>{col_w[2]}} "
        f"{'Qtd':>{col_w[3]}} {'CI kW':>{col_w[4]}} {'FP':>{col_w[5]}} "
        f"{'CI kVA':>{col_w[6]}} {'FD':>{col_w[7]}} {'D kW':>{col_w[8]}} {'D kVA':>{col_w[9]}}"
    )
    sep = '-' * len(header_line)
    body_lines = [header, header_line, sep]
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
        f"{'TOTAL':<{col_w[0]}} {'Demanda de projeto — conferir no local':<{col_w[1]}} "
        f"{'—':>{col_w[2]}} {'—':>{col_w[3]}} "
        f"{_fmt_br(totals['ci_kw']):>{col_w[4]}} {'—':>{col_w[5]}} "
        f"{_fmt_br(totals['ci_kva']):>{col_w[6]}} {'—':>{col_w[7]}} "
        f"{_fmt_br(totals['d_kw']):>{col_w[8]}} {_fmt_br(totals['d_kva']):>{col_w[9]}}"
    )
    body_lines.append('')
    body_lines.append(
        'Observação: rascunho de referência gerado automaticamente. '
        'Substituir cargas, FP e FD pelos valores reais levantados in loco antes do protocolo.'
    )
    if source == 'ai':
        body_lines.append('Fonte: composição sugerida por IA — validação técnica obrigatória.')
    else:
        body_lines.append('Fonte: modelo escalado por demanda-alvo informada.')
    return '\n'.join(body_lines)


def _ai_demand_prompt(target_kw: float, classe: str, client_name: str, uc: str, notes: str) -> str:
    return f"""Monte um levantamento de carga elétrica plausível para memorial descritivo.
Classe: {classe}
Demanda-alvo total D (kW): {target_kw}
Cliente: {client_name or 'não informado'}
UC: {uc or 'não informada'}
Contexto adicional: {notes or 'nenhum'}

Retorne APENAS JSON válido:
{{
  "rows": [
    {{
      "descricao": "nome da carga",
      "pot_w": 1000,
      "qtd": 2,
      "fp": 0.90,
      "fd": 0.80
    }}
  ]
}}
Use entre 4 e 8 itens. A soma de pot_w*qtd/1000*fd deve ficar próxima de {target_kw} kW."""


def _loads_from_ai(target_kw: float, classe: str, client_name: str, uc: str, notes: str):
    specs, source = _query_specs(_ai_demand_prompt(target_kw, classe, client_name, uc, notes))
    if not specs or 'rows' not in specs:
        return None, 'none'
    loads = []
    for row in specs['rows']:
        if not row.get('descricao'):
            continue
        loads.append({
            'descricao': row['descricao'],
            'pot_w': float(row.get('pot_w') or row.get('potencia_w') or 1000),
            'qtd': float(row.get('qtd') or row.get('quantidade') or 1),
            'fp': float(row.get('fp') or row.get('fator_potencia') or 0.9),
            'fd': float(row.get('fd') or row.get('fator_demanda') or 0.8),
        })
    if not loads:
        return None, 'none'
    rows = _rows_from_loads(loads)
    rows = _scale_rows_to_target(rows, target_kw)
    return rows, source


def generate_demand_table(
    target_kw: float,
    classe: str = 'INDUSTRIAL',
    client_name: str = '',
    uc: str = '',
    notes: str = '',
    prefer_ai: bool = False,
) -> dict[str, Any]:
    """Gera tabela de demanda escalada para target_kw."""
    target_kw = float(target_kw)
    if target_kw <= 0:
        raise ValueError('Demanda-alvo deve ser maior que zero')

    source = 'template'
    rows = None
    if prefer_ai and ai_available():
        rows, ai_source = _loads_from_ai(target_kw, classe, client_name, uc, notes)
        if rows:
            source = f'ai:{ai_source}'

    if rows is None:
        loads = RESIDENTIAL_LOADS if 'RESID' in classe.upper() else REFERENCE_LOADS
        rows = _rows_from_loads(loads)
        rows = _scale_rows_to_target(rows, target_kw)
        source = 'template'

    totals = _totals(rows)
    memorial_text = _rows_to_memorial_text(
        rows, totals, client_name, uc, classe, target_kw, source.split(':')[0],
    )

    return {
        'target_kw': target_kw,
        'classe': classe,
        'headers': HEADERS,
        'rows': rows,
        'totals': totals,
        'memorial_text': memorial_text,
        'source': source,
        'disclaimer': (
            'Tabela de referência — não substitui levantamento de campo. '
            'Conferir FP, FD e simultaneidade antes do protocolo.'
        ),
    }
