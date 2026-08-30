"""
Exporta tokens para AutoCAD (tokens_autocad.txt) — mesmos valores do memorial/DOCX.
Template DWG: templates/projeto_Modelo.dwg
"""

from __future__ import annotations

import re
from pathlib import Path

from figura_localizacao import FIGURA_TOKEN, resolve_lat_lon_from_values

FIGURA_PNG = 'figura_localizacao.png'
TOKENS_FILE = 'tokens_autocad.txt'

# Tokens usados no projeto_Modelo.dwg (carimbo + bloco técnico)
AUTOCAD_TOKEN_KEYS = (
    'CIDADE', 'UF', 'BAIRRO', 'ENDERECO_COMPLETO', 'ENDERECO',
    'POTENCIA_GERACAO', 'POTENCIA_TOTAL_INSTALADA', 'POTENCIA_INVERSOR_TOTAL',
    'POTENCIA_PAINEL_KWP', 'POTENCIA_INVERSOR_KWP', 'POTENCIA_MODULO_KWP',
    'CONTA_CONTRATO', 'CONTA_CONTRATO_DIGITOS', 'NOME_CLIENTE', 'CPF',
    'QTD_MODULOS', 'QTD_MODULOS_2D', 'POTENCIA_MODULO', 'FABRICANTE_MODULO', 'MODELO_MODULO',
    'QTD_INVERSORES', 'QTD_INVERSORES_2D', 'FABRICANTE_INVERSOR', 'MODELO_INVERSOR',
    'POTENCIA_INVERSOR', 'POTENCIA_INVERSOR_UNITARIO', 'TIPO_EQUIPAMENTO_INVERSOR',
)


def _num(text) -> float | None:
    if text is None:
        return None
    try:
        return float(str(text).replace(',', '.').strip())
    except (TypeError, ValueError):
        return None


def _fmt_br(value: float, decimals: int = 2) -> str:
    s = f'{value:.{decimals}f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _pad2(text) -> str:
    n = _num(text)
    if n is None:
        return str(text or '').strip()
    return f'{int(n):02d}'


def enrich_autocad_values(values: dict[str, str]) -> dict[str, str]:
    out = dict(values)

    qtd_m = _num(out.get('QTD_MODULOS'))
    pw = _num(out.get('POTENCIA_MODULO'))
    if qtd_m is not None and pw is not None:
        kwp_mod = qtd_m * pw / 1000
        out.setdefault('POTENCIA_TOTAL_INSTALADA', _fmt_br(kwp_mod, 2))
        out.setdefault('POTENCIA_PAINEL_KWP', _fmt_br(kwp_mod, 2))
    if pw is not None:
        out.setdefault('POTENCIA_MODULO_KWP', _fmt_br(pw / 1000, 2))

    inv_tot = _num(out.get('POTENCIA_INVERSOR_TOTAL') or out.get('POTENCIA_GERACAO'))
    if inv_tot is not None:
        out.setdefault('POTENCIA_INVERSOR_KWP', _fmt_br(inv_tot, 1))
        out.setdefault('POTENCIA_GERACAO', _fmt_br(inv_tot, 1))

    if out.get('QTD_MODULOS'):
        out.setdefault('QTD_MODULOS_2D', _pad2(out['QTD_MODULOS']))
    if out.get('QTD_INVERSORES'):
        out.setdefault('QTD_INVERSORES_2D', _pad2(out['QTD_INVERSORES']))

    if out.get('CIDADE') and out.get('UF'):
        out.setdefault('CIDADE_UF', f"{out['CIDADE']} - {out['UF']}")

    from gerar_documentos import normalize_conta_contrato

    uc = out.get('CONTA_CONTRATO_DIGITOS') or out.get('CONTA_CONTRATO')
    if uc:
        digits = normalize_conta_contrato(uc)
        out['CONTA_CONTRATO_DIGITOS'] = digits
        out['CONTA_CONTRATO'] = digits

    return out


def ensure_figura_png(values: dict[str, str], output_dir: Path) -> bool:
    """Gera figura_localizacao.png se houver coordenadas (mesma do memorial)."""
    png_path = output_dir / FIGURA_PNG
    if png_path.is_file():
        return True
    coords = resolve_lat_lon_from_values(values)
    if not coords:
        return False
    try:
        from figura_localizacao import generate_figura_png, zoom_from_values
        generate_figura_png(coords[0], coords[1], png_path, zoom=zoom_from_values(values))
        return png_path.is_file()
    except Exception:
        return False


def write_autocad_tokens_file(output_dir: Path, values: dict[str, str]) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_figura_png(values, output_dir)
    enriched = enrich_autocad_values(values)
    lines = [
        '# tokens_autocad.txt — Automação Equatorial PIENG',
        '# Template: templates/projeto_Modelo.dwg / projeto_Modelo.dxf',
        '# Saída CAD: planta.dwg (tokens preenchidos; fallback planta.dxf se ODA ausente)',
        '# Mapa: figura_localizacao.png — recorte Win+Shift+S e colar no AutoCAD',
        '# Formato: TOKEN=valor (sem chaves; no DWG use {{TOKEN}})',
        '',
    ]
    for key in AUTOCAD_TOKEN_KEYS:
        val = enriched.get(key, '')
        if val is None:
            val = ''
        val = str(val).replace('\r', ' ').replace('\n', ' ')
        lines.append(f'{key}={val}')

    # Demais tokens preenchidos (exceto internos)
    skip = set(AUTOCAD_TOKEN_KEYS) | {'__DEMAND_TABLE_JSON__', FIGURA_TOKEN}
    extras = []
    for key, val in sorted(enriched.items()):
        if key in skip or key.startswith('_'):
            continue
        if not val or not str(val).strip():
            continue
        if not re.match(r'^[A-Z0-9_]+$', key):
            continue
        extras.append((key, str(val).replace('\r', ' ').replace('\n', ' ')))
    if extras:
        lines.append('')
        lines.append('# Outros tokens disponíveis')
        for key, val in extras:
            lines.append(f'{key}={val}')

    path = output_dir / TOKENS_FILE
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path
