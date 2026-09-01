"""
Gera e insere figura de localização (mapa + pin) no memorial descritivo.

Padrão: tiles OpenStreetMap.de (osmde) + zoom automático (18 urbano / 16 rural ou OSM vazio).
Google Static Maps se GOOGLE_MAPS_API_KEY + prefer_google=True.
"""

from __future__ import annotations

import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw

from coordinate_utils import resolve_coordinates

USER_AGENT = 'EquatorialAutomacao/1.0 (figura localizacao; uso interno PIENG)'
TILE_SIZE = 256

# Camadas raster com nomes de ruas (sem API key). Padrão: osmde.
TILE_PROVIDERS: dict[str, dict[str, Any]] = {
    'esri': {
        'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        'subdomains': None,
        'attribution': '© Esri, OpenStreetMap contributors',
    },
    'osmde': {
        'url': 'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
        'subdomains': None,
        'attribution': '© OpenStreetMap contributors',
    },
    'osm': {
        'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        'subdomains': None,
        'attribution': '© OpenStreetMap contributors',
    },
    # Carto Voyager exige API key desde 2024 — use CARTO_API_KEY se tiver conta.
    'voyager': {
        'url': 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
        'subdomains': ('a', 'b', 'c', 'd'),
        'attribution': '© OpenStreetMap contributors © CARTO',
        'api_key_env': 'CARTO_API_KEY',
        'api_key_param': 'api_key',
    },
}

DEFAULT_TILE_PROVIDER = 'osmde'
ZOOM_URBAN = 18
ZOOM_RURAL = 16
DEFAULT_MAP_ZOOM = ZOOM_URBAN

FIGURA_TOKEN = 'FIGURA_LOCALIZACAO'
FIGURA_PLACEHOLDER = '[Inserir figura / print do mapa da localização]'

DOCX_PLACEHOLDERS = (
    f'{{{{{FIGURA_TOKEN}}}}}',
    FIGURA_PLACEHOLDER,
    'Figura tirado do maps da localização do imóvel',
)


def zoom_from_values(values: dict[str, str]) -> int | None:
    """Zoom escolhido na UI (FIGURA_MAP_ZOOM). None = automático urbano/rural."""
    raw = values.get('FIGURA_MAP_ZOOM') or values.get('figura_map_zoom')
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text or text == 'auto':
        return None
    try:
        level = int(text)
    except ValueError:
        return None
    return level if 10 <= level <= 20 else None


def resolve_tile_provider(name: str | None = None) -> dict[str, Any]:
    """FIGURA_MAP_TILE=osmde|osm|esri|voyager (padrão: osmde)."""
    key = (name or os.environ.get('FIGURA_MAP_TILE') or DEFAULT_TILE_PROVIDER).strip().lower()
    return TILE_PROVIDERS.get(key, TILE_PROVIDERS[DEFAULT_TILE_PROVIDER])


def resolve_lat_lon_from_values(values: dict[str, str]) -> tuple[float, float] | None:
    """Obtém lat/lon a partir dos tokens já montados (UTM ou graus decimais)."""
    raw_parts = [
        values.get('COORDENADAS'),
        values.get('COORDENADAS_GEORREFERENCIADAS'),
        values.get('coordenadas_raw'),
    ]
    raw_text = ' / '.join(p for p in raw_parts if p and str(p).strip())

    resolved = resolve_coordinates(
        utm_x=values.get('COORDENADA_UTM_X') or values.get('coordenada_utm_x'),
        utm_y=values.get('COORDENADA_UTM_Y') or values.get('coordenada_utm_y'),
        fuso_utm=values.get('FUSO_UTM') or values.get('fuso_utm'),
        latitude=values.get('LATITUDE') or values.get('latitude'),
        longitude=values.get('LONGITUDE') or values.get('longitude'),
        raw_text=raw_text or None,
    )
    lat = resolved.get('latitude') or resolved.get('LATITUDE')
    lon = resolved.get('longitude') or resolved.get('LONGITUDE')
    if lat is None or lon is None:
        return None
    try:
        return float(str(lat).replace(',', '.')), float(str(lon).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def latlon_to_pixel(
    lat: float,
    lon: float,
    zoom: int,
    origin_tile_x: int,
    origin_tile_y: int,
) -> tuple[float, float]:
    n = 2 ** zoom
    world_x = (lon + 180.0) / 360.0 * n * TILE_SIZE
    lat_rad = math.radians(lat)
    world_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE
    return world_x - origin_tile_x * TILE_SIZE, world_y - origin_tile_y * TILE_SIZE


def _fetch_tile(
    session: requests.Session,
    provider: dict[str, Any],
    zoom: int,
    x: int,
    y: int,
) -> Image.Image:
    subdomains = provider.get('subdomains')
    subdomain = ''
    if subdomains:
        subdomain = subdomains[(x + y) % len(subdomains)]
    url = provider['url'].format(s=subdomain, z=zoom, x=x, y=y)
    params = {}
    api_env = provider.get('api_key_env')
    if api_env:
        api_key = os.environ.get(api_env, '').strip()
        if not api_key:
            raise requests.RequestException(f'{api_env} não configurada para camada {provider}')
        param = provider.get('api_key_param', 'api_key')
        params[param] = api_key
    response = session.get(url, timeout=25, params=params if params else None)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert('RGB')


def _fetch_tile_with_fallback(
    session: requests.Session,
    zoom: int,
    x: int,
    y: int,
    primary_key: str | None = None,
) -> Image.Image | None:
    """Tenta provedor principal e fallbacks — evita quadrado cinza por tile ausente."""
    keys = []
    if primary_key:
        keys.append(primary_key)
    for k in ('osmde', 'osm', 'esri'):
        if k not in keys:
            keys.append(k)
    for key in keys:
        provider = TILE_PROVIDERS.get(key)
        if not provider:
            continue
        try:
            return _fetch_tile(session, provider, zoom, x, y)
        except requests.RequestException:
            continue
    return None


def _draw_pin(draw: ImageDraw.ImageDraw, x: float, y: float, size: int = 28) -> None:
    cx, cy = int(x), int(y)
    r = size // 2
    draw.ellipse([cx - r, cy - size + 4, cx + r, cy + 4], fill='#E53935', outline='#B71C1C', width=2)
    draw.ellipse([cx - r // 3, cy - size + 8, cx + r // 3, cy - size + r // 2 + 4], fill='white')


def _resolve_zoom(zoom: int | None = None) -> int | None:
    """None = automático (urbano/rural). Inteiro fixo se passado ou FIGURA_MAP_ZOOM definido."""
    if zoom is not None:
        return zoom
    env = os.environ.get('FIGURA_MAP_ZOOM', '').strip().lower()
    if not env or env == 'auto':
        return None
    if env.isdigit():
        return int(env)
    return None


def _nominatim_reverse(lat: float, lon: float) -> dict[str, Any]:
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'pt',
            },
            headers={'User-Agent': USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


def _reverse_geocode_label_from_nominatim(data: dict[str, Any]) -> str:
    addr = data.get('address') or {}
    parts = [
        addr.get('road') or addr.get('pedestrian'),
        addr.get('suburb') or addr.get('neighbourhood') or addr.get('quarter'),
        addr.get('city') or addr.get('town') or addr.get('municipality'),
    ]
    return ' — '.join(p for p in parts if p)


def _reverse_geocode_label(lat: float, lon: float) -> str:
    """Rua / bairro / cidade via Nominatim (complementa tiles quando faltam rótulos)."""
    return _reverse_geocode_label_from_nominatim(_nominatim_reverse(lat, lon))


def _is_rural_address(data: dict[str, Any]) -> bool:
    addr = data.get('address') or {}
    place_type = str(data.get('type') or '').lower()
    place_class = str(data.get('class') or '').lower()

    if any(addr.get(k) for k in ('hamlet', 'isolated_dwelling', 'farm', 'farmyard')):
        return True
    if place_type in ('village', 'hamlet', 'isolated_dwelling', 'farm', 'farmland'):
        return True
    if place_class == 'landuse' and place_type in ('farmland', 'meadow', 'forest', 'grass'):
        return True
    if addr.get('village') and not (
        addr.get('suburb') or addr.get('neighbourhood') or addr.get('city') or addr.get('town')
    ):
        return True
    if not (addr.get('road') or addr.get('pedestrian')):
        return True
    return False


def _tile_looks_sparse(tile: Image.Image, *, min_color_buckets: int = 22) -> bool:
    """Poucos tons no tile central → OSM vazio ou área sem detalhes (comum em rural/chácara)."""
    buckets: set[tuple[int, int, int]] = set()
    w, h = tile.size
    step = 8
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = tile.getpixel((x, y))
            buckets.add((r // 32, g // 32, b // 32))
            if len(buckets) >= min_color_buckets:
                return False
    return True


def _resolve_zoom_for_location(
    lat: float,
    lon: float,
    *,
    zoom: int | None = None,
    nominatim_data: dict[str, Any] | None = None,
    tile_provider: str | None = None,
) -> int:
    try:
        from app_settings import resolve_figura_zoom
        resolved = resolve_figura_zoom(zoom)
        if resolved is not None:
            return resolved
    except ImportError:
        fixed = _resolve_zoom(zoom)
        if fixed is not None:
            return fixed

    data = nominatim_data if nominatim_data is not None else _nominatim_reverse(lat, lon)
    if _is_rural_address(data):
        return ZOOM_RURAL

    provider_key = (tile_provider or os.environ.get('FIGURA_MAP_TILE') or DEFAULT_TILE_PROVIDER).strip().lower()
    center_x, center_y = latlon_to_tile(lat, lon, ZOOM_URBAN)
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    try:
        center_tile = _fetch_tile_with_fallback(session, ZOOM_URBAN, center_x, center_y, provider_key)
        if center_tile and _tile_looks_sparse(center_tile):
            return ZOOM_RURAL
    except requests.RequestException:
        pass
    return ZOOM_URBAN


def _add_caption(
    img: Image.Image,
    lat: float,
    lon: float,
    source: str,
    *,
    place_label: str | None = None,
) -> Image.Image:
    place = place_label if place_label is not None else _reverse_geocode_label(lat, lon)
    lines = [f'{lat:.6f}, {lon:.6f}']
    if place:
        lines.append(place)
    lines.append(source)
    bar_h = 12 + len(lines) * 18
    out = Image.new('RGB', (img.width, img.height + bar_h), (255, 255, 255))
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    for i, line in enumerate(lines):
        color = '#888888' if i == len(lines) - 1 else '#333333'
        draw.text((12, img.height + 8 + i * 18), line, fill=color)
    return out


def build_map_tiles(
    lat: float,
    lon: float,
    *,
    zoom: int = 18,
    tiles_radius: int = 2,
    crop_size: tuple[int, int] = (900, 650),
    tile_provider: str | None = None,
    place_label: str | None = None,
) -> Image.Image:
    provider_key = (tile_provider or os.environ.get('FIGURA_MAP_TILE') or DEFAULT_TILE_PROVIDER).strip().lower()
    try:
        from app_settings import get_figura_settings
        provider_key = get_figura_settings().get('tile_provider') or provider_key
        tiles_radius = get_figura_settings().get('tiles_radius') or tiles_radius
    except ImportError:
        pass

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
            tile = _fetch_tile_with_fallback(session, zoom, tx, ty, provider_key)
            if tile is not None:
                canvas.paste(tile, (dx * TILE_SIZE, dy * TILE_SIZE))

    pin_x, pin_y = latlon_to_pixel(lat, lon, zoom, origin_x, origin_y)
    draw = ImageDraw.Draw(canvas)
    _draw_pin(draw, pin_x, pin_y)

    tw, th = crop_size
    left = max(0, min(int(pin_x - tw // 2), canvas.width - tw))
    top = max(0, min(int(pin_y - th // 2), canvas.height - th))
    canvas = canvas.crop((left, top, left + tw, top + th))
    return _add_caption(canvas, lat, lon, TILE_PROVIDERS.get(provider_key, TILE_PROVIDERS[DEFAULT_TILE_PROVIDER])['attribution'], place_label=place_label)


def build_map_osm(
    lat: float,
    lon: float,
    *,
    zoom: int = 18,
    tiles_radius: int = 2,
    crop_size: tuple[int, int] = (900, 650),
) -> Image.Image:
    """Compatibilidade — usa FIGURA_MAP_TILE ou Voyager por padrão."""
    return build_map_tiles(
        lat, lon, zoom=zoom, tiles_radius=tiles_radius, crop_size=crop_size
    )


def build_map_google(
    lat: float,
    lon: float,
    api_key: str,
    *,
    zoom: int = 18,
    width: int = 900,
    height: int = 650,
) -> Image.Image:
    params = {
        'center': f'{lat},{lon}',
        'zoom': str(zoom),
        'size': f'{min(width, 640)}x{min(height, 640)}',
        'maptype': 'hybrid',
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
    return _add_caption(img, lat, lon, 'Google Maps')


def generate_figura_png(
    lat: float,
    lon: float,
    output_path: Path,
    *,
    zoom: int | None = None,
    tiles_radius: int = 2,
    prefer_google: bool = False,
    tile_provider: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nominatim_data = _nominatim_reverse(lat, lon)
    place_label = _reverse_geocode_label_from_nominatim(nominatim_data)
    resolved_zoom = _resolve_zoom_for_location(
        lat, lon, zoom=zoom, nominatim_data=nominatim_data, tile_provider=tile_provider
    )
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()
    if prefer_google and api_key:
        img = build_map_google(lat, lon, api_key, zoom=resolved_zoom)
    else:
        img = build_map_tiles(
            lat,
            lon,
            zoom=resolved_zoom,
            tiles_radius=tiles_radius,
            tile_provider=tile_provider,
            place_label=place_label,
        )
    img.save(output_path, 'PNG', optimize=True)
    return output_path


def insert_figura_into_docx(docx_path: Path, png_path: Path, *, width_cm: float = 14.0) -> bool:
    from docx_media import insert_image_at_placeholders
    return insert_image_at_placeholders(docx_path, png_path, DOCX_PLACEHOLDERS, width_cm=width_cm)


def try_embed_figura_localizacao(
    memorial_docx: Path,
    values: dict[str, str],
    output_dir: Path,
    *,
    zoom: int | None = None,
) -> tuple[bool, str]:
    """
    Gera PNG a partir das coordenadas e insere no memorial já preenchido.
    Retorna (sucesso, mensagem para relatório).
    """
    coords = resolve_lat_lon_from_values(values)
    if not coords:
        return False, (
            'Figura do mapa não inserida — informe Coordenada UTM X/Y + Fuso '
            'ou Latitude/Longitude no formulário.'
        )

    lat, lon = coords
    png_path = output_dir / 'figura_localizacao.png'
    effective_zoom = zoom if zoom is not None else zoom_from_values(values)
    try:
        generate_figura_png(lat, lon, png_path, zoom=effective_zoom)
        if not insert_figura_into_docx(memorial_docx, png_path):
            return False, (
                'Figura do mapa gerada, mas o marcador não foi encontrado no memorial '
                '(verifique {{FIGURA_LOCALIZACAO}} no template).'
            )
        return True, 'Figura do mapa inserida no memorial.'
    except Exception as exc:
        return False, f'Figura do mapa não inserida — {exc}'
