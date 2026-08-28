"""
Insere {{TABELA_DEMANDA}} no memorial abaixo do título "Tabela 1 – Levantamento de Carga".
Substitui a tabela estática do Word pelo placeholder de texto.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

TOKEN = '{{TABELA_DEMANDA}}'
TITLE_MARK = 'Tabela 1'
PLACEHOLDER_PARAGRAPH = (
    '<w:p><w:r><w:t xml:space="preserve">'
    + TOKEN
    + '</w:t></w:r></w:p>'
)


def _find_table_bounds(xml: str, start_idx: int) -> tuple[int, int] | None:
    tbl_start = xml.find('<w:tbl>', start_idx)
    if tbl_start < 0:
        return None
    depth = 0
    pos = tbl_start
    while pos < len(xml):
        if xml.startswith('<w:tbl', pos):
            depth += 1
        if xml.startswith('</w:tbl>', pos):
            depth -= 1
            if depth == 0:
                return tbl_start, pos + len('</w:tbl>')
        pos += 1
    return None


def patch_memorial_template(template_path: Path) -> bool:
    """Retorna True se alterou o arquivo."""
    if not template_path.exists():
        return False
    with zipfile.ZipFile(template_path, 'r') as zin:
        if 'word/document.xml' not in zin.namelist():
            return False
        doc_xml = zin.read('word/document.xml').decode('utf-8')

    if TOKEN in doc_xml:
        return False

    title_idx = doc_xml.find(TITLE_MARK)
    if title_idx < 0:
        return False

    bounds = _find_table_bounds(doc_xml, title_idx)
    if not bounds:
        # Sem tabela: insere parágrafo logo após o título
        end_p = doc_xml.find('</w:p>', title_idx)
        if end_p < 0:
            return False
        insert_at = end_p + len('</w:p>')
        new_xml = doc_xml[:insert_at] + PLACEHOLDER_PARAGRAPH + doc_xml[insert_at:]
    else:
        tbl_start, tbl_end = bounds
        new_xml = doc_xml[:tbl_start] + PLACEHOLDER_PARAGRAPH + doc_xml[tbl_end:]

    backup = template_path.with_suffix('.docx.bak')
    if not backup.exists():
        shutil.copy2(template_path, backup)

    tmp = template_path.with_suffix('.docx.tmp')
    with zipfile.ZipFile(template_path, 'r') as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                data = new_xml.encode('utf-8')
            zout.writestr(item, data)
    tmp.replace(template_path)
    return True


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    path = root / 'templates' / 'MEMORIAL_DESCRITIVO_marcadores.docx'
    ok = patch_memorial_template(path)
    print('patched' if ok else 'skipped', path)
