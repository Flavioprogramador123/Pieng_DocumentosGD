"""Testes GUIA 0 — linhas de inversores no formulário NT."""
import unittest
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from gerar_documentos import (
    _find_worksheet_cell,
    _set_worksheet_inline_string,
    _trim_guia0_inverter_rows,
    _worksheet_cell_text,
    fill_workbook,
    build_values,
    load_defaults,
    parse_txt_content,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates' / 'NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xlsx'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def _filled_inverter_rows(sheet_xml: bytes) -> int:
    root = etree.fromstring(sheet_xml)
    count = 0
    for row in range(22, 32):
        if _worksheet_cell_text(_find_worksheet_cell(root, f'D{row}')).strip():
            count += 1
    return count


class TestGuia0InverterTrim(unittest.TestCase):
    def test_trim_keeps_only_qtd_inversores_rows(self):
        with ZipFile(TEMPLATE) as z:
            sheet1 = z.read('xl/worksheets/sheet1.xml')
        root = etree.fromstring(sheet1)
        for row in range(22, 32):
            cell = _find_worksheet_cell(root, f'D{row}')
            if cell is not None:
                _set_worksheet_inline_string(cell, 'Fabricante Teste')
        _trim_guia0_inverter_rows(root, {'QTD_INVERSORES': '8'})
        filled = sum(
            1 for row in range(22, 32)
            if _worksheet_cell_text(_find_worksheet_cell(root, f'D{row}')).strip()
        )
        self.assertEqual(filled, 8)

    def test_fill_workbook_8_microinversores(self):
        if not TEMPLATE.exists():
            self.skipTest('template ausente')
        raw = parse_txt_content(
            'Quantidade de Inversores: 8\n'
            'Quantidade de Módulos: 32\n'
            'Potência Nominal dos Inversores (kW): 2.25\n'
            'Fabricante dos Inversores: Teste\n'
            'Modelo dos Inversores: Micro X\n'
            'Tipo de Inversor: MICRO\n'
            'Tipo de Ligação: TRIFASICO\n'
            'Classe: RESIDENCIAL\n'
            'Tensão de Atendimento (V): 220V\n'
            'Disjuntor de Entrada (A): 40\n'
        )
        config = ROOT / 'backend' / 'config_padrao.json'
        values = build_values(raw, load_defaults(config))
        out = ROOT / 'backend' / '_test_out_nt.xlsx'
        try:
            fill_workbook(TEMPLATE, out, values)
            with ZipFile(out) as z:
                filled = _filled_inverter_rows(z.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(filled, 8, f'esperado 8 linhas de inversor, obteve {filled}')
        finally:
            if out.exists():
                out.unlink()


if __name__ == '__main__':
    unittest.main()
