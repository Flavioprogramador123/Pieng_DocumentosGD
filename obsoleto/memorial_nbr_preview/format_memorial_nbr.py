"""
Formata memorial DOCX conforme ABNT/NBR (relatório técnico):
  - Margens: 3 cm esquerda, 2 cm demais (NBR 14725)
  - Fonte: Arial 12 pt, entrelinha 1,5
  - Tabelas: bordas uniformes, cabeçalho 1ª linha em negrito/fundo cinza

Uso:
  python format_memorial_nbr.py --input ../templates_backup/MEMORIAL...PRE_NBR.docx \\
      --output preview_output/MEMORIAL_DESCRITIVO_marcadores_NBR.docx
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W_NS}

# twips: 1 cm ≈ 567
MAR_LEFT = '1701'   # 3 cm
MAR_OTHER = '1134'  # 2 cm
LINE_15 = '360'     # 1,5 linhas
FONT_SIZE = '24'    # 12 pt (half-points)
FONT_NAME = 'Arial'
HEADER_FILL = 'E7E6E6'


def _q(tag: str) -> str:
    return f'{{{W_NS}}}{tag}'


def _ensure_child(parent, tag: str):
    node = parent.find(_q(tag))
    if node is None:
        node = etree.SubElement(parent, _q(tag))
    return node


def _set_margins(root) -> None:
    for sect in root.xpath('.//w:sectPr', namespaces=NS):
        pg_mar = _ensure_child(sect, 'pgMar')
        pg_mar.set(_q('left'), MAR_LEFT)
        pg_mar.set(_q('right'), MAR_OTHER)
        pg_mar.set(_q('top'), MAR_OTHER)
        pg_mar.set(_q('bottom'), MAR_OTHER)
        pg_mar.set(_q('header'), '708')
        pg_mar.set(_q('footer'), '708')
        pg_mar.set(_q('gutter'), '0')


def _apply_paragraph_format(p) -> None:
    p_pr = p.find(_q('pPr'))
    if p_pr is None:
        p_pr = etree.Element(_q('pPr'))
        p.insert(0, p_pr)
    spacing = _ensure_child(p_pr, 'spacing')
    spacing.set(_q('line'), LINE_15)
    spacing.set(_q('lineRule'), 'auto')
    spacing.set(_q('after'), '120')
    jc = p_pr.find(_q('jc'))
    if jc is not None:
        p_pr.remove(jc)


def _apply_run_font(r, bold: bool = False) -> None:
    r_pr = r.find(_q('rPr'))
    if r_pr is None:
        r_pr = etree.SubElement(r, _q('rPr'))
    fonts = _ensure_child(r_pr, 'rFonts')
    fonts.set(_q('ascii'), FONT_NAME)
    fonts.set(_q('hAnsi'), FONT_NAME)
    fonts.set(_q('cs'), FONT_NAME)
    sz = _ensure_child(r_pr, 'sz')
    sz.set(_q('val'), FONT_SIZE)
    sz_cs = _ensure_child(r_pr, 'szCs')
    sz_cs.set(_q('val'), FONT_SIZE)
    if bold:
        b = r_pr.find(_q('b'))
        if b is None:
            etree.SubElement(r_pr, _q('b'))
    else:
        b = r_pr.find(_q('b'))
        if b is not None:
            r_pr.remove(b)


def _table_borders(tbl) -> None:
    tbl_pr = tbl.find(_q('tblPr'))
    if tbl_pr is None:
        tbl_pr = etree.Element(_q('tblPr'))
        tbl.insert(0, tbl_pr)
    borders = tbl_pr.find(_q('tblBorders'))
    if borders is not None:
        tbl_pr.remove(borders)
    borders = etree.SubElement(tbl_pr, _q('tblBorders'))
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = etree.SubElement(borders, _q(edge))
        el.set(_q('val'), 'single')
        el.set(_q('sz'), '4')
        el.set(_q('space'), '0')
        el.set(_q('color'), '000000')
    tbl_w = tbl_pr.find(_q('tblW'))
    if tbl_w is None:
        tbl_w = etree.SubElement(tbl_pr, _q('tblW'))
    tbl_w.set(_q('type'), 'pct')
    tbl_w.set(_q('w'), '5000')


def _format_table(tbl) -> None:
    _table_borders(tbl)
    rows = tbl.xpath('./w:tr', namespaces=NS)
    for ri, tr in enumerate(rows):
        is_header = ri == 0
        for tc in tr.xpath('./w:tc', namespaces=NS):
            tc_pr = tc.find(_q('tcPr'))
            if tc_pr is None:
                tc_pr = etree.SubElement(tc, _q('tcPr'))
            if is_header:
                shd = tc_pr.find(_q('shd'))
                if shd is None:
                    shd = etree.SubElement(tc_pr, _q('shd'))
                shd.set(_q('val'), 'clear')
                shd.set(_q('color'), 'auto')
                shd.set(_q('fill'), HEADER_FILL)
            for p in tc.xpath('.//w:p', namespaces=NS):
                _apply_paragraph_format(p)
                for r in p.xpath('.//w:r', namespaces=NS):
                    _apply_run_font(r, bold=is_header)


def format_document_xml(data: bytes) -> bytes:
    root = etree.fromstring(data)
    _set_margins(root)
    body = root.find(_q('body'))
    if body is not None:
        for child in body:
            tag = etree.QName(child.tag).localname
            if tag == 'p':
                _apply_paragraph_format(child)
                for r in child.xpath('.//w:r', namespaces=NS):
                    _apply_run_font(r)
            elif tag == 'tbl':
                _format_table(child)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def _patch_styles(styles_data: bytes) -> bytes:
    root = etree.fromstring(styles_data)
    for style in root.xpath('//w:style', namespaces=NS):
        stype = style.get(_q('type'))
        if stype != 'paragraph':
            continue
        sid = style.get(_q('styleId'), '')
        r_pr = style.find(_q('rPr'))
        if r_pr is None:
            r_pr = etree.SubElement(style, _q('rPr'))
        fonts = _ensure_child(r_pr, 'rFonts')
        fonts.set(_q('ascii'), FONT_NAME)
        fonts.set(_q('hAnsi'), FONT_NAME)
        sz = _ensure_child(r_pr, 'sz')
        sz.set(_q('val'), FONT_SIZE)
        p_pr = style.find(_q('pPr'))
        if p_pr is None:
            p_pr = etree.SubElement(style, _q('pPr'))
        spacing = _ensure_child(p_pr, 'spacing')
        spacing.set(_q('line'), LINE_15)
        spacing.set(_q('lineRule'), 'auto')
        if sid.lower().startswith('heading') or 'titulo' in sid.lower():
            b = r_pr.find(_q('b'))
            if b is None:
                etree.SubElement(r_pr, _q('b'))
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def format_memorial_docx(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source, 'r') as zin, ZipFile(destination, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                data = format_document_xml(data)
            elif item.filename == 'word/styles.xml':
                data = _patch_styles(data)
            zout.writestr(item, data)


def main() -> None:
    parser = argparse.ArgumentParser(description='Formata memorial DOCX (NBR/ABNT).')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    format_memorial_docx(args.input, args.output)
    print(f'OK: {args.output}')


if __name__ == '__main__':
    main()
