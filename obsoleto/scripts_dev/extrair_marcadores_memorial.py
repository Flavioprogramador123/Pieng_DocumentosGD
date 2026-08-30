"""Extrai linhas marcadas do memorial: {{TOKEN}}, **variável**, +cálculo+."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / 'templates' / 'MEMORIAL_DESCRITIVO_marcadores.docx'
OUT_TXT = ROOT / 'dados' / 'memorial_linhas_marcadas.txt'


def main() -> None:
    with zipfile.ZipFile(DOCX) as z:
        xml = z.read('word/document.xml').decode('utf-8', errors='ignore')

    plain = re.sub(r'</w:p>', '\n', xml)
    plain = re.sub(r'<[^>]+>', '', plain)

    lines_out: list[str] = []
    for i, line in enumerate(plain.split('\n'), 1):
        line = re.sub(r'\s+', ' ', line).strip()
        if not line:
            continue
        has_token = '{{' in line
        has_star = '**' in line
        has_plus = bool(re.search(r'\+[^+]{3,}\+', line))
        if has_token or has_star or has_plus:
            kind: list[str] = []
            if has_token:
                kind.append('TOKEN')
            if has_star:
                kind.append('**')
            if has_plus:
                kind.append('+calc+')
            lines_out.append(f'L{i:04d} [{"|".join(kind)}] {line[:220]}')

    OUT_TXT.write_text('\n'.join(lines_out), encoding='utf-8')
    print(f'{len(lines_out)} linhas -> {OUT_TXT}')


if __name__ == '__main__':
    main()
