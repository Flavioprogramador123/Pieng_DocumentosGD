#!/usr/bin/env python3
"""Gera tamanhos do logo PIENG para UI e ícones (a partir do PNG mestre)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'logopieng-removebg-preview.png'
OUT_BACKEND = ROOT
OUT_FRONTEND = ROOT.parents[1] / 'equatorial_automation_frontend' / 'public' / 'brand'

SIZES = {
    'logo-app-48.png': 48,
    'logo-app-96.png': 96,
    'icon-32.png': 32,
    'icon-180.png': 180,
    'icon-192.png': 192,
    'icon-512.png': 512,
}


def resize_square(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f'Arquivo mestre não encontrado: {SOURCE}')

    master = Image.open(SOURCE).convert('RGBA')
    OUT_FRONTEND.mkdir(parents=True, exist_ok=True)

    for name, px in SIZES.items():
        out = resize_square(master, px)
        for folder in (OUT_BACKEND, OUT_FRONTEND):
            target = folder / name
            out.save(target, 'PNG', optimize=True)
            print(f'OK {target} ({px}×{px})')

    print('\nFrontend: /brand/logo-app-48.png')
    print('Favicon:  /brand/icon-32.png')


if __name__ == '__main__':
    main()
