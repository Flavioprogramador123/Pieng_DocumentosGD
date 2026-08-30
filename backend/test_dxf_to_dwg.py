"""Teste manual: DXF → DWG com ODA File Converter."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dxf_to_dwg import convert_dxf_to_dwg, find_oda_converter


def main() -> int:
    oda = find_oda_converter()
    print(f'ODA File Converter: {oda or "NAO ENCONTRADO"}')
    if not oda:
        print('Instale ODA ou defina ODA_FILE_CONVERTER no .env')
        return 1

    template_dxf = ROOT / 'templates' / 'projeto_Modelo.dxf'
    if not template_dxf.is_file():
        print(f'Template ausente: {template_dxf}')
        return 1

    with tempfile.TemporaryDirectory(prefix='pieng_planta_test_') as tmp:
        out_dir = Path(tmp)
        dxf = out_dir / 'planta.dxf'
        dwg = out_dir / 'planta.dwg'

        import shutil
        shutil.copy2(template_dxf, dxf)
        print(f'DXF origem: {dxf.stat().st_size / 1024 / 1024:.1f} MB')

        ok = convert_dxf_to_dwg(dxf, dwg)
        if not ok:
            print('FALHA na conversao')
            return 1

        print(f'OK: {dwg} ({dwg.stat().st_size / 1024 / 1024:.1f} MB)')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
