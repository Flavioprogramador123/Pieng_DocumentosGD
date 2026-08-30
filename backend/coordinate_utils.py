"""
Parse e conversão de coordenadas (Google Earth, UTM WGS84, graus decimais).
"""

from __future__ import annotations

import math
import re
from typing import Any

# WGS84
_WGS84_A = 6378137.0
_WGS84_F = 1 / 298.257223563
_WGS84_E2 = _WGS84_F * (2 - _WGS84_F)
_WGS84_EP2 = _WGS84_E2 / (1 - _WGS84_E2)
_WGS84_K0 = 0.9996


def _sf(val, default=None):
    if val in (None, ''):
        return default
    try:
        return float(str(val).replace(',', '.').strip())
    except (TypeError, ValueError):
        return default


def _fmt_coord(value: float, decimals: int = 6) -> str:
    return f'{value:.{decimals}f}'.rstrip('0').rstrip('.') if decimals else str(value)


def zone_from_longitude(lon: float) -> int:
    return int((lon + 180) // 6) + 1


def parse_fuso_utm(text: str | None) -> tuple[int, bool, str]:
    """
    Interpreta fuso UTM: '22S', '22 K', '22', 'fuso 22S'.
    Retorna (zone, southern, label) ex.: (22, True, '22S').
    """
    if not text:
        return 22, True, '22S'
    raw = str(text).strip().upper()
    m = re.search(r'(\d{1,2})', raw)
    if not m:
        return 22, True, '22S'
    zone = int(m.group(1))
    if re.search(r'\bS\b', raw) or raw.endswith('S'):
        southern = True
    elif re.search(r'\bN\b', raw) and not re.search(r'\bS\b', raw):
        southern = False
    else:
        southern = True  # padrão Equatorial GO / centro-oeste
    label = f'{zone}{"S" if southern else "N"}'
    return zone, southern, label


def utm_to_latlon(
    easting: float,
    northing: float,
    zone: int,
    *,
    southern: bool = True,
) -> tuple[float, float]:
    """UTM WGS84 → (lat, lon) graus decimais."""
    x = easting - 500_000.0
    y = northing - (10_000_000.0 if southern else 0.0)

    e = math.sqrt(_WGS84_E2)
    e1 = (1 - math.sqrt(1 - _WGS84_E2)) / (1 + math.sqrt(1 - _WGS84_E2))
    long_origin = math.radians((zone - 1) * 6 - 180 + 3)

    m = y / _WGS84_K0
    mu = m / (_WGS84_A * (1 - _WGS84_E2 / 4 - 3 * _WGS84_E2 ** 2 / 64 - 5 * _WGS84_E2 ** 3 / 256))

    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
        + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
        + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
        + (1097 * e1 ** 4 / 512) * math.sin(8 * mu)
    )

    sin_phi = math.sin(phi1)
    cos_phi = math.cos(phi1)
    tan_phi = math.tan(phi1)

    n1 = _WGS84_A / math.sqrt(1 - _WGS84_E2 * sin_phi ** 2)
    t1 = tan_phi ** 2
    c1 = _WGS84_EP2 * cos_phi ** 2
    r1 = _WGS84_A * (1 - _WGS84_E2) / (1 - _WGS84_E2 * sin_phi ** 2) ** 1.5
    d = x / (n1 * _WGS84_K0)

    lat = phi1 - (n1 * tan_phi / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * _WGS84_EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * _WGS84_EP2 - 3 * c1 ** 2)
        * d ** 6
        / 720
    )
    lon = long_origin + (
        d
        - (1 + 2 * t1 + c1) * d ** 3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * _WGS84_EP2 + 24 * t1 ** 2)
        * d ** 5
        / 120
    ) / cos_phi

    return math.degrees(lat), math.degrees(lon)


def latlon_to_utm(
    lat: float,
    lon: float,
    zone: int | None = None,
) -> tuple[float, float, int, bool, str]:
    """(lat, lon) graus → (easting, northing, zone, southern, label)."""
    zone = zone or zone_from_longitude(lon)
    southern = lat < 0
    phi = math.radians(lat)
    lam = math.radians(lon)
    long_origin = math.radians((zone - 1) * 6 - 180 + 3)

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)
    n = _WGS84_A / math.sqrt(1 - _WGS84_E2 * sin_phi ** 2)
    t = tan_phi ** 2
    c = _WGS84_EP2 * cos_phi ** 2
    a_val = cos_phi * (lam - long_origin)

    m = _WGS84_A * (
        (1 - _WGS84_E2 / 4 - 3 * _WGS84_E2 ** 2 / 64 - 5 * _WGS84_E2 ** 3 / 256) * phi
        - (3 * _WGS84_E2 / 8 + 3 * _WGS84_E2 ** 2 / 32 + 45 * _WGS84_E2 ** 3 / 1024)
        * math.sin(2 * phi)
        + (15 * _WGS84_E2 ** 2 / 256 + 45 * _WGS84_E2 ** 3 / 1024) * math.sin(4 * phi)
        - (35 * _WGS84_E2 ** 3 / 3072) * math.sin(6 * phi)
    )

    easting = _WGS84_K0 * n * (
        a_val
        + (1 - t + c) * a_val ** 3 / 6
        + (5 - 18 * t + t ** 2 + 72 * c - 58 * _WGS84_EP2) * a_val ** 5 / 120
    ) + 500_000.0

    northing = _WGS84_K0 * (
        m
        + n
        * tan_phi
        * (
            a_val ** 2 / 2
            + (5 - t + 9 * c + 4 * c ** 2) * a_val ** 4 / 24
            + (61 - 58 * t + t ** 2 + 600 * c - 330 * _WGS84_EP2) * a_val ** 6 / 720
        )
    )
    if southern:
        northing += 10_000_000.0

    label = f'{zone}{"S" if southern else "N"}'
    return easting, northing, zone, southern, label


# Google Earth: "22 K 722658.18 m E 8193755.57 m S / -16.326994° -48.915886°"
_GOOGLE_EARTH_RE = re.compile(
    r'(\d{1,2})\s*([A-HJ-NP-Z])\s+'
    r'([\d.,]+)\s*m\s*E\s*,?\s+'
    r'([\d.,]+)\s*m\s*([NS])'
    r'(?:\s*/?\s*(-?\d+[.,]\d+)\s*°?\s+(-?\d+[.,]\d+)\s*°?)?',
    re.IGNORECASE,
)

# Graus decimais: "-16.326994, -48.915886" ou "-16.326994° -48.915886°"
_LATLON_RE = re.compile(
    r'(-?\d{1,2}[.,]\d+)\s*°?\s*[,/\s]\s*(-?\d{1,3}[.,]\d+)\s*°?',
)

# UTM solto: "722658.18 m E" ... "8193755.57 m S"
_UTM_PAIR_RE = re.compile(
    r'([\d.,]+)\s*m\s*E.*?([\d.,]+)\s*m\s*([NS])',
    re.IGNORECASE,
)


def parse_coordinate_text(text: str | None) -> dict[str, Any]:
    """Extrai UTM e/ou lat/lon de texto livre (Google Earth, memorial, TXT)."""
    if not text or not str(text).strip():
        return {}

    raw = str(text).strip()
    out: dict[str, Any] = {}

    m = _GOOGLE_EARTH_RE.search(raw)
    if m:
        zone = int(m.group(1))
        band = m.group(2).upper()
        easting = _sf(m.group(3))
        northing = _sf(m.group(4))
        hem = m.group(5).upper()
        southern = hem == 'S' or band >= 'N'
        out['utm_x'] = easting
        out['utm_y'] = northing
        out['zone'] = zone
        out['southern'] = southern
        out['fuso_utm'] = f'{zone}{"S" if southern else "N"}'
        if m.group(6) and m.group(7):
            out['latitude'] = _sf(m.group(6))
            out['longitude'] = _sf(m.group(7))
        return out

    m = _LATLON_RE.search(raw)
    if m:
        out['latitude'] = _sf(m.group(1))
        out['longitude'] = _sf(m.group(2))
        return out

    m = _UTM_PAIR_RE.search(raw)
    if m:
        out['utm_x'] = _sf(m.group(1))
        out['utm_y'] = _sf(m.group(2))
        southern = m.group(3).upper() == 'S'
        out['southern'] = southern
        zm = re.search(r'(\d{1,2})\s*[A-HJ-NP-Z]', raw, re.I)
        if zm:
            zone = int(zm.group(1))
            out['zone'] = zone
            out['fuso_utm'] = f'{zone}{"S" if southern else "N"}'
        return out

    return {}


def resolve_coordinates(
    *,
    utm_x=None,
    utm_y=None,
    fuso_utm=None,
    latitude=None,
    longitude=None,
    raw_text=None,
) -> dict[str, str]:
    """
    Preenche campos faltantes convertendo UTM ↔ graus decimais.
    Retorna dict com chaves para tokens TXT/memorial.
    """
    parsed = parse_coordinate_text(raw_text) if raw_text else {}

    easting = _sf(utm_x) or parsed.get('utm_x')
    northing = _sf(utm_y) or parsed.get('utm_y')
    lat = _sf(latitude) or parsed.get('latitude')
    lon = _sf(longitude) or parsed.get('longitude')

    zone, southern, fuso_label = parse_fuso_utm(fuso_utm or parsed.get('fuso_utm'))
    if parsed.get('zone'):
        zone = int(parsed['zone'])
    if 'southern' in parsed:
        southern = bool(parsed['southern'])
        fuso_label = f'{zone}{"S" if southern else "N"}'
    elif fuso_utm:
        zone, southern, fuso_label = parse_fuso_utm(fuso_utm)

    # UTM → lat/lon
    if easting is not None and northing is not None and (lat is None or lon is None):
        lat, lon = utm_to_latlon(easting, northing, zone, southern=southern)

    # lat/lon → UTM
    if lat is not None and lon is not None and (easting is None or northing is None):
        easting, northing, zone, southern, fuso_label = latlon_to_utm(lat, lon, zone)

    if easting is None and northing is None and lat is None and lon is None:
        return {}

    result: dict[str, str] = {}
    if easting is not None:
        result['COORDENADA_UTM_X'] = _fmt_coord(easting, 2)
        result['coordenada_utm_x'] = result['COORDENADA_UTM_X']
    if northing is not None:
        result['COORDENADA_UTM_Y'] = _fmt_coord(northing, 2)
        result['coordenada_utm_y'] = result['COORDENADA_UTM_Y']
    if fuso_label:
        result['FUSO_UTM'] = fuso_label
        result['fuso_utm'] = fuso_label
    if lat is not None:
        result['LATITUDE'] = _fmt_coord(lat, 6)
        result['latitude'] = result['LATITUDE']
    if lon is not None:
        result['LONGITUDE'] = _fmt_coord(lon, 6)
        result['longitude'] = result['LONGITUDE']
    return result


def enrich_coordinate_tokens(values: dict[str, str]) -> dict[str, str]:
    """Aplica resolve_coordinates sobre dict de tokens (gerar_documentos)."""
    raw_parts = [
        values.get('COORDENADAS'),
        values.get('COORDENADAS_GEORREFERENCIADAS'),
    ]
    raw_text = ' / '.join(p for p in raw_parts if p and str(p).strip())

    resolved = resolve_coordinates(
        utm_x=values.get('COORDENADA_UTM_X'),
        utm_y=values.get('COORDENADA_UTM_Y'),
        fuso_utm=values.get('FUSO_UTM'),
        latitude=values.get('LATITUDE'),
        longitude=values.get('LONGITUDE'),
        raw_text=raw_text or None,
    )
    for key, val in resolved.items():
        if key.isupper():
            values.setdefault(key, val)
        else:
            # aliases minúsculos — só se token maiúsculo ainda vazio
            upper = key.upper()
            if upper not in values or not str(values.get(upper, '')).strip():
                values.setdefault(upper, val)
    return values


def enrich_normalized_coordinates(normalized: dict) -> None:
    """Preenche uc + dados_tecnicos no payload normalizado."""
    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})

    raw = tec.get('coordenadas_raw') or uc.get('coordenadas_raw') or ''
    resolved = resolve_coordinates(
        utm_x=uc.get('coordenada_utm_x') or tec.get('coordenada_utm_x'),
        utm_y=uc.get('coordenada_utm_y') or tec.get('coordenada_utm_y'),
        fuso_utm=uc.get('fuso_utm') or tec.get('fuso_utm'),
        latitude=tec.get('latitude'),
        longitude=tec.get('longitude'),
        raw_text=raw or None,
    )
    if not resolved:
        return

    if resolved.get('coordenada_utm_x'):
        uc.setdefault('coordenada_utm_x', resolved['coordenada_utm_x'])
        tec.setdefault('coordenada_utm_x', resolved['coordenada_utm_x'])
    if resolved.get('coordenada_utm_y'):
        uc.setdefault('coordenada_utm_y', resolved['coordenada_utm_y'])
        tec.setdefault('coordenada_utm_y', resolved['coordenada_utm_y'])
    if resolved.get('fuso_utm'):
        uc.setdefault('fuso_utm', resolved['fuso_utm'])
        tec.setdefault('fuso_utm', resolved['fuso_utm'])
    if resolved.get('latitude'):
        tec.setdefault('latitude', resolved['latitude'])
    if resolved.get('longitude'):
        tec.setdefault('longitude', resolved['longitude'])
