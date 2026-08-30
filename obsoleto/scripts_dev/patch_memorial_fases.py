"""Patch memorial: tokens dinâmicos para conexão inversores e disjuntor de entrada."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

from patch_memorial_legado import DOCX, NS, element_text, replace_in_element, text_nodes

REPLACEMENTS = [
    (
        'conectados em fases distintas do sistema trifásico para balanceamento de carga',
        '{{DESCRICAO_CONEXAO_INVERSORES}}',
    ),
    (
        'Proteção: Disjuntor tripolar {{CORRENTE_ENTRADA}} A (curva {{CURVA_ATUACAO_DISJUNTOR}})',
        'Proteção: {{DESCRICAO_DISJUNTOR_PADRAO}} {{CORRENTE_ENTRADA}} A (curva {{CURVA_ATUACAO_DISJUNTOR}})',
    ),
]


def main() -> None:
    if not DOCX.exists():
        raise SystemExit(f'Arquivo não encontrado: {DOCX}')

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DOCX.with_suffix(f'.docx.bak_{stamp}')
    shutil.copy2(DOCX, backup)
    print(f'Backup: {backup.name}')

    with ZipFile(DOCX, 'r') as zin:
        entries = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    root = etree.fromstring(entries['word/document.xml'])
    count = 0
    for paragraph in root.xpath('.//w:p', namespaces=NS):
        text = element_text(paragraph)
        for old, new in REPLACEMENTS:
            if old in text and replace_in_element(paragraph, old, new):
                count += 1

    entries['word/document.xml'] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True
    )
    with ZipFile(DOCX, 'w', ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)

    print(f'Substituições: {count}')
    print(f'Atualizado: {DOCX}')


if __name__ == '__main__':
    main()
