#!/usr/bin/env python3
"""Lista {{TOKENS}} em arquivo DXF (exporte o DWG como DXF no AutoCAD)."""

import re
import sys
from pathlib import Path


def scan_dxf(path: Path) -> set[str]:
    text = path.read_text(encoding='utf-8', errors='ignore')
    found = set(re.findall(r'\{\{[A-Z0-9_]+\}\}', text, flags=re.I))
    # MTEXT do AutoCAD às vezes grava \{ \{TOKEN\} \}
    for m in re.finditer(r'\\?\{\\?\{([A-Z0-9_]+)\\?\}\\?\}', text, flags=re.I):
        found.add('{{' + m.group(1).upper() + '}}')
    return found


def main():
    if len(sys.argv) < 2:
        print('Uso: python list_dwg_tokens.py caminho/arquivo.dxf')
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_file():
        print('Arquivo não encontrado:', path)
        sys.exit(1)
    tokens = {t.upper() for t in scan_dxf(path)}
    print(f'Tokens em {path.name}: {len(tokens)}')
    for t in sorted(tokens):
        print(' ', t)


if __name__ == '__main__':
    main()
