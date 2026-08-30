#!/usr/bin/env python3
"""
Protótipo (.temp) — figura de localização a partir de coordenadas.

Gera PNG estilo print do Maps (ruas + pin vermelho) usando tiles OpenStreetMap.
Não altera o projeto principal; se funcionar bem, integrar depois em gerar_documentos.

Uso:
  python gerar_figura_maps.py --lat -16.326990 --lon -48.915934
  python gerar_figura_maps.py --txt ..\\..\\saida\\web_generated\\...\\dados_cliente.txt
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from coordinate_utils import parse_coordinate_text, resolve_coordinates  # noqa: E402

USER_AGENT = 'EquatorialMapsPrototype/1.0 (.temp; uso local pontual)'
TILE_SIZE = 256
TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'


def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def latlon_to_pixel(lat: float, lon: float, zoom: int, origin_tile_x: int, origin_tile_y: int) -> tuple[float, float]:
    n = 2 ** zoom
    world_x = (lon + 180.0) / 360.0 * n * TILE_SIZE
    lat_rad = math.radians(lat)
    world_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE
    return world_x - origin_tile_x * TILE_SIZE, world_y - origin_tile_y * TILE_SIZE


def fetch_tile(session: requests.Session, zoom: int, x: int, y: int) -> Image.Image:
    url = TILE_URL.format(z=zoom, x=x, y=y)
    response = session.get(url, timeout=25)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert('RGB')


def draw_pin(draw: ImageDraw.ImageDraw, x: float, y: float, size: int = 28) -> None:
    """Pin vermelho simplificado (estilo Google Maps)."""
    cx, cy = int(x), int(y)
    r = size // 2
    draw.ellipse([cx - r, cy - size + 4, cx + r, cy + 4], fill='#E53935', outline='#B71C1C', width=2)
    draw.ellipse([cx - r // 3, cy - size + 8, cx + r // 3, cy - size + r // 2 + 4], fill='white')


def add_caption(img: Image.Image, lat: float, lon: float) -> Image.Image:
    """Rodapé com coordenadas (como no print do Maps)."""
    bar_h = 36
    out = Image.new('RGB', (img.width, img.height + bar_h), (255, 255, 255))
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    text = f'{lat:.6f}, {lon:.6f}  |  OpenStreetMap (protótipo .temp)'
    draw.text((12, img.height + 10), text, fill='#333333')
    return out


def build_map_osm(
    lat: float,
    lon: float,
    *,
    zoom: int = 18,
    tiles_radius: int = 2,
    crop_size: tuple[int, int] | None = (900, 650),
) -> Image.Image:
    center_x, center_y = latlon_to_tile(lat, lon, zoom)
    origin_x = center_x - tiles_radius
    origin_y = center_y - tiles_radius
    grid = tiles_radius * 2 + 1

    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    canvas = Image.new('RGB', (grid * TILE_SIZE, grid * TILE_SIZE), (238, 238, 238))
    for dy in range(grid):
        for dx in range(grid):
            tx, ty = origin_x + dx, origin_y + dy
            try:
                tile = fetch_tile(session, zoom, tx, ty)
            except requests.RequestException as exc:
                print(f'[aviso] tile {zoom}/{tx}/{ty}: {exc}')
                continue
            canvas.paste(tile, (dx * TILE_SIZE, dy * TILE_SIZE))

    pin_x, pin_y = latlon_to_pixel(lat, lon, zoom, origin_x, origin_y)
    draw = ImageDraw.Draw(canvas)
    draw_pin(draw, pin_x, pin_y)

    if crop_size:
        tw, th = crop_size
        left = max(0, min(int(pin_x - tw // 2), canvas.width - tw))
        top = max(0, min(int(pin_y - th // 2), canvas.height - th))
        canvas = canvas.crop((left, top, left + tw, top + th))

    return add_caption(canvas, lat, lon)


def build_map_google(
    lat: float,
    lon: float,
    api_key: str,
    *,
    zoom: int = 18,
    width: int = 900,
    height: int = 650,
    maptype: str = 'hybrid',
) -> Image.Image:
    """Opcional: vista satélite/híbrida (requer GOOGLE_MAPS_API_KEY)."""
    params = {
        'center': f'{lat},{lon}',
        'zoom': str(zoom),
        'size': f'{min(width, 640)}x{min(height, 640)}',
        'maptype': maptype,
        'markers': f'color:red|{lat},{lon}',
        'key': api_key,
        'scale': '2',
    }
    response = requests.get(
        'https://maps.googleapis.com/maps/api/staticmap',
        params=params,
        timeout=30,
        headers={'User-Agent': USER_AGENT},
    )
    response.raise_for_status()
    img = Image.open(BytesIO(response.content)).convert('RGB')
    if img.width != width or img.height != height:
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    return add_caption(img, lat, lon)


def coords_from_txt(path: Path) -> tuple[float, float]:
    text = path.read_text(encoding='utf-8-sig')
    lat = lon = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            label, value = line.split(':', 1)
            key = label.lower().strip()
            value = value.strip()
            if key in ('latitude', 'lat'):
                lat = float(value.replace(',', '.'))
            elif key in ('longitude', 'lon', 'lng', 'long'):
                lon = float(value.replace(',', '.'))
            elif 'coordenada' in key:
                parsed = parse_coordinate_text(value)
                lat = lat or parsed.get('latitude')
                lon = lon or parsed.get('longitude')
        else:
            match = re.search(r'(-?\d{1,2}\.\d+)\s*[,/\s]\s*(-?\d{1,3}\.\d+)', line)
            if match:
                lat = float(match.group(1))
                lon = float(match.group(2))

    resolved = resolve_coordinates(latitude=lat, longitude=lon, raw_text=text)
    if resolved.get('latitude') and resolved.get('longitude'):
        return float(resolved['latitude']), float(resolved['longitude'])

    raise ValueError(f'Coordenadas não encontradas em {path}')


def default_output(lat: float, lon: float) -> Path:
    out_dir = Path(__file__).parent / 'saida'
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_lat = str(lat).replace('.', '_').replace('-', 'm')
    safe_lon = str(lon).replace('.', '_').replace('-', 'm')
    return out_dir / f'figura_localizacao_{safe_lat}_{safe_lon}.png'


def main() -> int:
    parser = argparse.ArgumentParser(description='Gera figura de localização (protótipo .temp)')
    parser.add_argument('--lat', type=float, help='Latitude decimal (WGS84)')
    parser.add_argument('--lon', type=float, help='Longitude decimal (WGS84)')
    parser.add_argument('--txt', type=Path, help='Arquivo TXT com coordenadas (dados_cliente.txt)')
    parser.add_argument('--zoom', type=int, default=18, help='17 = mais contexto; 18 = lotes (padrão)')
    parser.add_argument('--raio', type=int, default=2, help='Tiles em cada direção (2 → grade 5×5)')
    parser.add_argument('--largura', type=int, default=900)
    parser.add_argument('--altura', type=int, default=650)
    parser.add_argument('--google', action='store_true', help='Usar Google Static Maps (requer API key)')
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()

    if args.txt:
        lat, lon = coords_from_txt(args.txt)
    elif args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    else:
        parser.error('Informe --lat/--lon ou --txt')

    output = args.output or default_output(lat, lon)
    output.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()
    if args.google and api_key:
        img = build_map_google(lat, lon, api_key, zoom=args.zoom, width=args.largura, height=args.altura)
        source = 'Google Static Maps (hybrid)'
    else:
        if args.google and not api_key:
            print('[aviso] GOOGLE_MAPS_API_KEY não definida; usando OpenStreetMap.')
        img = build_map_osm(
            lat,
            lon,
            zoom=args.zoom,
            tiles_radius=args.raio,
            crop_size=(args.largura, args.altura),
        )
        source = 'OpenStreetMap'

    img.save(output, 'PNG', optimize=True)
    print(f'OK: {output}')
    print(f'Fonte: {source}')
    print(f'Coordenadas: {lat:.6f}, {lon:.6f}')
    print(f'Google Maps: https://www.google.com/maps?q={lat},{lon}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
