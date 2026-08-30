"""
Gera blocos OOXML (w:p, w:tbl) para a tabela de demanda no memorial Word.
"""

from __future__ import annotations

import json
from typing import Any

from lxml import etree

from demand_table import HEADERS, _fmt_br, _fmt_pct

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W_NS}


def _w(tag: str) -> str:
    return f'{{{W_NS}}}{tag}'


def _para(text: str, *, bold: bool = False, center: bool = False, size_half_pt: int = 16) -> etree._Element:
    p = etree.Element(_w('p'))
    if center:
        ppr = etree.SubElement(p, _w('pPr'))
        etree.SubElement(ppr, _w('jc'), {_w('val'): 'center'})
    r = etree.SubElement(p, _w('r'))
    if bold or size_half_pt != 22:
        rpr = etree.SubElement(r, _w('rPr'))
        if bold:
            etree.SubElement(rpr, _w('b'))
        if size_half_pt != 22:
            etree.SubElement(rpr, _w('sz'), {_w('val'): str(size_half_pt)})
            etree.SubElement(rpr, _w('szCs'), {_w('val'): str(size_half_pt)})
    t = etree.SubElement(r, _w('t'))
    if text[:1].isspace() or text[-1:].isspace():
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return p


def _cell(text: str, *, bold: bool = False, center: bool = False, width_dxa: int = 900) -> etree._Element:
    tc = etree.Element(_w('tc'))
    tcpr = etree.SubElement(tc, _w('tcPr'))
    etree.SubElement(tcpr, _w('tcW'), {_w('w'): str(width_dxa), _w('type'): 'dxa'})
    tc.append(_para(text, bold=bold, center=center))
    return tc


def _row(cells: list[tuple[str, bool, bool]]) -> etree._Element:
    tr = etree.Element(_w('tr'))
    widths = [700, 3200, 1100, 700, 900, 700, 900, 700, 900, 900]
    for idx, (text, bold, center) in enumerate(cells):
        tr.append(_cell(text, bold=bold, center=center, width_dxa=widths[idx] if idx < len(widths) else 900))
    return tr


def _table_borders() -> etree._Element:
    tbl_borders = etree.Element(_w('tblBorders'))
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        etree.SubElement(
            tbl_borders,
            _w(edge),
            {
                _w('val'): 'single',
                _w('sz'): '4',
                _w('space'): '0',
                _w('color'): 'auto',
            },
        )
    return tbl_borders


def build_demand_table_elements(data: dict[str, Any]) -> list[etree._Element]:
    """Retorna w:tbl a partir do dict de generate_demand_table (sem textos explicativos)."""
    rows = data.get('rows') or []
    totals = data.get('totals') or {}

    elements: list[etree._Element] = []

    tbl = etree.Element(_w('tbl'))
    tbl_pr = etree.SubElement(tbl, _w('tblPr'))
    etree.SubElement(tbl_pr, _w('tblW'), {_w('w'): '0', _w('type'): 'auto'})
    tbl_pr.append(_table_borders())

    grid = etree.SubElement(tbl, _w('tblGrid'))
    for w in (700, 3200, 1100, 700, 900, 700, 900, 700, 900, 900):
        etree.SubElement(grid, _w('gridCol'), {_w('w'): str(w)})

    header_cells = [(h, True, h != 'Descrição') for h in (data.get('headers') or HEADERS)]
    tbl.append(_row(header_cells))

    for row in rows:
        tbl.append(
            _row([
                (str(row.get('item', '')), False, True),
                (str(row.get('descricao', '')), False, False),
                (str(row.get('pot_unit_w', '')), False, True),
                (str(row.get('qtd', '')), False, True),
                (_fmt_br(float(row.get('ci_kw', 0))), False, True),
                (_fmt_br(float(row.get('fp', 0))), False, True),
                (_fmt_br(float(row.get('ci_kva', 0))), False, True),
                (_fmt_pct(float(row.get('fd', 0))), False, True),
                (_fmt_br(float(row.get('d_kw', 0))), False, True),
                (_fmt_br(float(row.get('d_kva', 0))), False, True),
            ])
        )

    tbl.append(
        _row([
            ('TOTAL', True, True),
            ('Demanda de projeto — conferir no local', True, False),
            ('—', False, True),
            ('—', False, True),
            (_fmt_br(float(totals.get('ci_kw', 0))), True, True),
            ('—', False, True),
            (_fmt_br(float(totals.get('ci_kva', 0))), True, True),
            ('—', False, True),
            (_fmt_br(float(totals.get('d_kw', 0))), True, True),
            (_fmt_br(float(totals.get('d_kva', 0))), True, True),
        ])
    )

    elements.append(tbl)
    return elements


def parse_demand_table_payload(raw: str | dict | None) -> dict[str, Any] | None:
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw if raw.get('rows') else None
    try:
        data = json.loads(str(raw))
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) and data.get('rows') else None


def rows_to_word_tsv(data: dict[str, Any]) -> str:
    """TSV para colar no Word: Inserir → Tabela → Converter texto em tabela."""
    headers = data.get('headers') or HEADERS
    lines = ['\t'.join(headers)]
    for row in data.get('rows') or []:
        lines.append(
            '\t'.join([
                str(row.get('item', '')),
                str(row.get('descricao', '')),
                str(row.get('pot_unit_w', '')),
                str(row.get('qtd', '')),
                _fmt_br(float(row.get('ci_kw', 0))),
                _fmt_br(float(row.get('fp', 0))),
                _fmt_br(float(row.get('ci_kva', 0))),
                _fmt_pct(float(row.get('fd', 0))),
                _fmt_br(float(row.get('d_kw', 0))),
                _fmt_br(float(row.get('d_kva', 0))),
            ])
        )
    totals = data.get('totals') or {}
    lines.append(
        '\t'.join([
            'TOTAL',
            'Demanda de projeto — conferir no local',
            '—',
            '—',
            _fmt_br(float(totals.get('ci_kw', 0))),
            '—',
            _fmt_br(float(totals.get('ci_kva', 0))),
            '—',
            _fmt_br(float(totals.get('d_kw', 0))),
            _fmt_br(float(totals.get('d_kva', 0))),
        ])
    )
    return '\n'.join(lines)
