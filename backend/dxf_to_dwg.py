"""
Conversão DXF → DWG via ODA File Converter (Windows).

Gera planta.dwg compacta para entrega ao cliente; o DXF intermediário é descartado
quando a conversão tem sucesso. Se o ODA não estiver instalado, retorna False
e o fluxo mantém planta.dxf (fallback).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_ODA_PATHS = (
    Path(r'C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe'),
    Path(r'C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe'),
    Path(r'C:\Program Files\ODA\ODAFileConverter 26.9.0\ODAFileConverter.exe'),
)

# Compatível com AutoCAD 2018+ (Equatorial / fluxo PIENG)
ODA_OUTPUT_VERSION = os.environ.get('ODA_OUTPUT_VERSION', 'ACAD2018')
ODA_TIMEOUT_SEC = int(os.environ.get('ODA_CONVERT_TIMEOUT', '180'))


def find_oda_converter() -> Path | None:
    """Localiza ODAFileConverter.exe (env ODA_FILE_CONVERTER ou caminhos padrão)."""
    env_path = (os.environ.get('ODA_FILE_CONVERTER') or '').strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    for path in DEFAULT_ODA_PATHS:
        if path.is_file():
            return path

    oda_root = Path(r'C:\Program Files\ODA')
    if oda_root.is_dir():
        for path in sorted(oda_root.glob('**/ODAFileConverter.exe')):
            if path.is_file():
                return path

    return None


def convert_dxf_to_dwg(dxf_path: Path, dwg_path: Path) -> bool:
    """
    Converte um arquivo DXF para DWG usando ODA File Converter.
    Retorna True se planta.dwg foi gerada com sucesso.
    """
    dxf_path = Path(dxf_path).resolve()
    dwg_path = Path(dwg_path).resolve()

    if not dxf_path.is_file():
        return False

    oda_exe = find_oda_converter()
    if not oda_exe:
        return False

    dwg_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='pieng_dxf_in_') as tmp_in, tempfile.TemporaryDirectory(
        prefix='pieng_dwg_out_'
    ) as tmp_out:
        input_dir = Path(tmp_in)
        output_dir = Path(tmp_out)
        staged_dxf = input_dir / dxf_path.name
        shutil.copy2(dxf_path, staged_dxf)

        cmd = [
            str(oda_exe),
            str(input_dir),
            str(output_dir),
            ODA_OUTPUT_VERSION,
            'DWG',
            '0',
            '1',
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=ODA_TIMEOUT_SEC,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False

        if result.returncode != 0:
            return False

        expected = output_dir / f'{dxf_path.stem}.dwg'
        converted = expected if expected.is_file() else None
        if converted is None:
            matches = list(output_dir.glob('*.dwg'))
            if not matches:
                return False
            converted = matches[0]

        if dwg_path.exists():
            dwg_path.unlink()
        shutil.move(str(converted), str(dwg_path))
        return dwg_path.is_file()
