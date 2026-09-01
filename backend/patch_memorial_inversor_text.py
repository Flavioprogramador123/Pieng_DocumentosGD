"""Corrige texto fixo de inversor no memorial — usa {{TIPO_EQUIPAMENTO_INVERSOR}}."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates' / 'MEMORIAL_DESCRITIVO_marcadores.docx'
TOKEN = '{{TIPO_EQUIPAMENTO_INVERSOR}}(es)'

# Ordem: padrões mais específicos primeiro
REPLACEMENTS = (
    ('micro inversores', TOKEN),
    ('inversor(es)', TOKEN),
)


def patch_memorial_inversor_text(template_path: Path = TEMPLATE) -> bool:
    if not template_path.exists():
        return False
    backup = template_path.with_suffix('.docx.bak_inversor')
    if not backup.exists():
        shutil.copy2(template_path, backup)

    with zipfile.ZipFile(template_path, 'r') as zin:
        doc_xml = zin.read('word/document.xml').decode('utf-8')

    original = doc_xml
    for old, new in REPLACEMENTS:
        if old in doc_xml:
            doc_xml = doc_xml.replace(old, new, 1)

    if doc_xml == original:
        return False

    tmp = template_path.with_suffix('.docx.tmp')
    with zipfile.ZipFile(template_path, 'r') as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                data = doc_xml.encode('utf-8')
            zout.writestr(item, data)
    tmp.replace(template_path)
    return True


if __name__ == '__main__':
    ok = patch_memorial_inversor_text()
    print('patched' if ok else 'skipped', TEMPLATE)
