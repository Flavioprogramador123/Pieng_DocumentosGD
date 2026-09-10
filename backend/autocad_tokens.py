"""
Exporta tokens para AutoCAD (tokens_autocad.txt) — mesmos valores do memorial/DOCX.
Template DWG: templates/projeto_Modelo.dwg
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
import math

from figura_localizacao import FIGURA_TOKEN, resolve_lat_lon_from_values

FIGURA_PNG = 'figura_localizacao.png'
TOKENS_FILE = 'tokens_autocad.txt'

# Tokens usados no projeto_Modelo.dwg (carimbo + bloco técnico)
AUTOCAD_TOKEN_KEYS = (
    'DATA', 'DATA_DOCUMENTO',
    'CIDADE', 'UF', 'BAIRRO', 'ENDERECO_COMPLETO', 'ENDERECO',
    'POTENCIA_GERACAO', 'POTENCIA_TOTAL_INSTALADA', 'POTENCIA_INVERSOR_TOTAL',
    'POTENCIA_PAINEL_KWP', 'POTENCIA_INVERSOR_KWP', 'POTENCIA_MODULO_KWP',
    'CONTA_CONTRATO', 'CONTA_CONTRATO_DIGITOS', 'NOME_CLIENTE', 'CPF',
    'QTD_MODULOS', 'QTD_MODULOS_2D', 'POTENCIA_MODULO', 'FABRICANTE_MODULO', 'MODELO_MODULO',
    'QTD_INVERSORES', 'QTD_INVERSORES_2D', 'FABRICANTE_INVERSOR', 'MODELO_INVERSOR',
    'POTENCIA_INVERSOR', 'POTENCIA_INVERSOR_UNITARIO', 'TIPO_EQUIPAMENTO_INVERSOR',
    'TEXTO_DIAGRAMA_MODULOS', 'TEXTO_DIAGRAMA_INVERSOR',
    'DISJUNTOR_CA_INVERSOR_A', 'DISJUNTOR_CA_PADRAO_A',
    'TEXTO_DISJUNTOR_CA_INVERSOR', 'TEXTO_DISJUNTOR_CA_PADRAO',
    'TEXTO_UNIFILAR_INVERSOR', 'TEXTO_UNIFILAR_MICRO',
    'TEXTO_UNIFILAR_STRING_1', 'TEXTO_UNIFILAR_STRING_2',
    'TEXTO_UNIFILAR_STRING_3', 'TEXTO_UNIFILAR_STRING_4',
    'TEXTO_UNIFILAR_MPPT_1', 'TEXTO_UNIFILAR_ARRANJO_1',
    'TEXTO_CABO_CC_UNIFILAR', 'TEXTO_CABO_CA_UNIFILAR', 'TEXTO_CABO_PADRAO_UNIFILAR',
    'TEXTO_POSTE_UNIFILAR',
)

MAX_UNIFILAR_STRINGS = 4


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


def _dc_context_from_values(out: dict[str, str]):
    qtd_m = _num(out.get('QTD_MODULOS'))
    qtd_i = _num(out.get('QTD_INVERSORES'))
    if not qtd_m or not qtd_i:
        return None
    modules = [{
        'quantidade': int(qtd_m),
        'voc': out.get('TENSAO_CIRCUITO_ABERTO'),
        'isc': out.get('CORRENTE_CURTO_CIRCUITO'),
        'vmpp': out.get('TENSAO_MAX_POTENCIA'),
        'impp': out.get('CORRENTE_MAX_POTENCIA'),
    }]
    inverters = [{
        'quantidade': int(qtd_i),
        'num_mppt': out.get('QTD_ENTRADAS_MPPT_INVERSOR') or out.get('NUM_MPPT'),
        'mppt_min': out.get('TENSAO_MPPT_MIN_INVERSOR'),
        'mppt_max': out.get('TENSAO_MPPT_MAX_INVERSOR'),
        'corrente_max_saida_ca': out.get('CORRENTE_MAX_SAIDA_CA_INVERSOR'),
        'tipo_inversor': out.get('TIPO_INVERSOR'),
        'fabricante': out.get('FABRICANTE_INVERSOR'),
        'modelo': out.get('MODELO_INVERSOR'),
        'potencia': out.get('POTENCIA_INVERSOR_UNITARIO') or out.get('POTENCIA_INVERSOR'),
    }]
    technical = {
        'tipo_inversor': out.get('TIPO_INVERSOR'),
        'num_mppt': out.get('NUM_MPPT') or out.get('QTD_ENTRADAS_MPPT_INVERSOR'),
        'modulos_por_string': out.get('MODULOS_POR_STRING'),
        'strings_por_mppt': out.get('STRINGS_POR_MPPT'),
        'micros_por_grupo_ca': out.get('MICROS_POR_GRUPO_CA'),
    }
    return modules, inverters, technical


def _ensure_string_layout_hints(out: dict[str, str]) -> None:
    """Evita tratar inversor string como micro quando MODULOS_POR_STRING não veio do form."""
    tipo = (out.get('TIPO_EQUIPAMENTO_INVERSOR') or out.get('TIPO_INVERSOR') or '').lower()
    if 'micro' in tipo:
        return
    if out.get('MODULOS_POR_STRING'):
        return
    total = _num(out.get('QTD_MODULOS'))
    inv = _num(out.get('QTD_INVERSORES'))
    if not total or not inv or total <= inv:
        return
    # Heurística: 1 string CC por inversor (ex.: 8 mód / 2 inv = 4 mód/string)
    mps = max(2, int(math.ceil(total / inv)))
    out.setdefault('MODULOS_POR_STRING', str(mps))
    out.setdefault('TIPO_INVERSOR', out.get('TIPO_INVERSOR') or 'STRING')


def _string_module_counts(total: int, strings_count: int, modules_per_string: int) -> list[int]:
    if strings_count <= 0 or total <= 0:
        return []
    mps = max(1, modules_per_string)
    counts: list[int] = []
    remaining = total
    for i in range(strings_count):
        if remaining <= 0:
            break
        if i == strings_count - 1:
            n = remaining
        else:
            n = min(mps, remaining)
        counts.append(n)
        remaining -= n
    return counts


def _bitola_mm2(text: str | None, default: str = '4') -> str:
    match = re.search(r'(\d+)', str(text or ''))
    return match.group(1) if match else default


def _nome_modulo_unifilar(fabricante: str, modelo: str, pot_wp: float | None = None) -> str:
    fab = str(fabricante or '').strip()
    mod = str(modelo or '').strip()
    if fab and mod:
        return f'{fab} {mod}'.strip()
    if mod:
        return mod
    if fab:
        return fab
    if pot_wp:
        return f'{int(pot_wp)} W'
    return '—'


def _format_cabo_cc_borracha(condutores: int, bitola_mm: str) -> str:
    return (
        f'{condutores}#{bitola_mm}mm² Borracha Livre de Halogênos, 90°C - '
        f'0.6/1kV (1.8kV CC) - \\PClasse 5'
    )


def _format_cabo_cc_string(bitola_mm: str = '4') -> str:
    return (
        f'2#{bitola_mm}mm² + PE 1#6mm²\\PBorracha Livre de Halogênos, 90°C - '
        f'0.6/1kV (1.8kV CC) - \\PClasse 5\\P'
    )


def _format_cabo_padrao_unifilar(bitola_padrao: str | None, *, num_condutores: int = 2) -> str:
    mm = _bitola_mm2(bitola_padrao, '10')
    return f'{num_condutores}#{mm} mm² -\\PPVC 70°C -\\P0,6/1 kV - \\PClasse 2'


def _format_poste_unifilar(num_poste: str | None) -> str:
    raw = str(num_poste or 'ilegível').strip()
    if not raw or raw.lower() in {'ilegível', 'ilegivel', 'ilégível'}:
        return '(POSTE N° \\PILÉGÍVEL)'
    return f'(POSTE N° \\P{raw.upper()})'


def _format_unifilar_string_mtext(
    index: int,
    mod_count: int,
    *,
    fabricante: str,
    modelo: str,
    pot_wp: float,
) -> str:
    pot_string = _fmt_br(mod_count * pot_wp / 1000, 1)
    nome = _nome_modulo_unifilar(fabricante, modelo, pot_wp)
    return (
        f'STRING {index}\\PMODULO SOLAR\\P{nome}\\PPOT STRING: {pot_string}kWP'
    )


def _format_unifilar_inversor_mtext(
    *,
    fabricante: str,
    modelo: str,
    pot_kw: float,
    tensao: str = '',
) -> str:
    pot = f'{pot_kw:.1f}'.replace('.', ',')
    fab = fabricante or '—'
    mod = modelo or '—'
    tail = f'\\P{tensao} \\P' if tensao else '\\P'
    return (
        f'INVERSOR \\PPOTÊNCIA NOMINAL CA: {pot}kW\\PFABRICANTE: {fab}\\PMODELO: {mod}{tail}'
    )


def _format_unifilar_micro_mtext(
    *,
    qtd: int,
    fabricante: str,
    modelo: str,
    pot_kw: float,
) -> str:
    pot = _fmt_br(pot_kw, 2)
    fab = fabricante or '—'
    mod = modelo or '—'
    return (
        f'{qtd} x Micro-Inversores marca {fab}, Modelo: {mod}, potência pico AC {pot} kW'
    )


def _format_unifilar_arranjo_mtext(
    mod_count: int,
    *,
    fabricante: str,
    modelo: str,
    pot_wp: float,
) -> str:
    pot_unit = _fmt_br(pot_wp / 1000, 2)
    pot_total = _fmt_br(mod_count * pot_wp / 1000, 2)
    nome = _nome_modulo_unifilar(fabricante, modelo, pot_wp)
    return (
        f'ARRANJO 01\\P{mod_count} x PAINEIS {nome}\\PPOT UNIT: {pot_unit} kWP\\PPOT ARRANJO:{pot_total} kWP'
    )


def apply_padrao_unifilar_tokens(out: dict[str, str]) -> dict[str, str]:
    """Cabo padrão de entrada, poste e disjuntor no diagrama unifilar."""
    from grid_voltage import resolve_ligacao_config

    ligacao = resolve_ligacao_config(out.get('TIPO_LIGACAO'))
    q_fase = int(ligacao.get('qtd_condutores_fase') or 1)
    q_neutro = int(ligacao.get('qtd_condutores_neutro') or 1)
    num_cond = q_fase + q_neutro

    out.setdefault(
        'TEXTO_CABO_PADRAO_UNIFILAR',
        _format_cabo_padrao_unifilar(out.get('BITOLA_CABO_PADRAO'), num_condutores=num_cond),
    )
    out.setdefault('TEXTO_POSTE_UNIFILAR', _format_poste_unifilar(out.get('NUM_POSTE')))

    disj_pad = str(
        out.get('DISJUNTOR_CA_PADRAO_A') or out.get('DISJUNTOR_ENTRADA') or '40'
    ).strip().upper().removesuffix('A')
    out.setdefault('DISJUNTOR_CA_PADRAO_A', disj_pad)
    return out


def apply_unifilar_tokens(out: dict[str, str]) -> dict[str, str]:
    """Textos MTEXT do diagrama unifilar (strings CC + bloco inversor)."""
    ctx = _dc_context_from_values(out)
    if not ctx:
        return out

    modules, inverters, technical = ctx
    _ensure_string_layout_hints(out)
    technical['modulos_por_string'] = out.get('MODULOS_POR_STRING')
    technical['tipo_inversor'] = out.get('TIPO_INVERSOR') or technical.get('tipo_inversor')
    try:
        from string_calculations import analyze_dc_strings

        dc = analyze_dc_strings(modules, inverters, technical)
    except Exception:
        return out

    fab_m = str(out.get('FABRICANTE_MODULO') or '').strip()
    mod_m = str(out.get('MODELO_MODULO') or '').strip()
    pot_wp = _num(out.get('POTENCIA_MODULO')) or 0.0
    fab_i = str(out.get('FABRICANTE_INVERSOR') or '').strip()
    mod_i = str(out.get('MODELO_INVERSOR') or '').strip()
    pot_inv = _num(out.get('POTENCIA_INVERSOR_UNITARIO') or out.get('POTENCIA_INVERSOR')) or 0.0
    tensao = str(out.get('TENSAO_SAIDA_INVERSOR') or out.get('TENSAO_ATENDIMENTO') or '').strip()
    if tensao and not tensao.upper().endswith(('V', 'A')):
        tensao = f'{tensao}Vca'

    topology = dc.get('topology', 'string')
    total_mod = int(dc.get('total_modules') or 0)
    strings_count = int(dc.get('strings_count') or 0)
    mps = int(dc.get('modules_per_string') or 1)
    inv_qty = int(dc.get('inverter_quantity') or 1)

    counts = _string_module_counts(total_mod, strings_count, mps)
    for idx in range(1, MAX_UNIFILAR_STRINGS + 1):
        key = f'TEXTO_UNIFILAR_STRING_{idx}'
        if idx <= len(counts) and pot_wp > 0:
            out[key] = _format_unifilar_string_mtext(
                idx, counts[idx - 1], fabricante=fab_m, modelo=mod_m, pot_wp=pot_wp,
            )
        else:
            out.setdefault(key, '')

    mppt_used = int(dc.get('mppt_used') or 1)
    out.setdefault('TEXTO_UNIFILAR_MPPT_1', f'\\C256;MPPT - {mppt_used:02d}')

    if topology == 'micro':
        bitola_cc = _bitola_mm2(out.get('BITOLA_CABO_CC'), '4')
        out.setdefault(
            'TEXTO_CABO_CC_UNIFILAR',
            _format_cabo_cc_borracha(max(1, total_mod * 2), bitola_cc),
        )
        bitola_ca = _bitola_mm2(out.get('BITOLA_CABO_CA'), '4')
        out.setdefault(
            'TEXTO_CABO_CA_UNIFILAR',
            f'2#{bitola_ca},0mm² 0,6/1kV\\PPVC 70°C - Classe 2\\P+ PE 1#6,00 mm²',
        )
        out.setdefault(
            'TEXTO_UNIFILAR_MICRO',
            _format_unifilar_micro_mtext(
                qtd=inv_qty, fabricante=fab_i, modelo=mod_i, pot_kw=pot_inv,
            ),
        )
        if total_mod > 0 and pot_wp > 0:
            out.setdefault(
                'TEXTO_UNIFILAR_ARRANJO_1',
                _format_unifilar_arranjo_mtext(
                    total_mod, fabricante=fab_m, modelo=mod_m, pot_wp=pot_wp,
                ),
            )
    elif pot_inv > 0:
        bitola_cc = _bitola_mm2(out.get('BITOLA_CABO_CC'), '4')
        out.setdefault('TEXTO_CABO_CC_UNIFILAR', _format_cabo_cc_string(bitola_cc))
        bitola_ca = _bitola_mm2(out.get('BITOLA_CABO_CA'), '6')
        out.setdefault(
            'TEXTO_CABO_CA_UNIFILAR',
            f'2#{bitola_ca},0mm² + 1#{bitola_ca},0mm² PE 0,6/1kV\\PPVC 70°C',
        )
        out.setdefault(
            'TEXTO_UNIFILAR_INVERSOR',
            _format_unifilar_inversor_mtext(
                fabricante=fab_i, modelo=mod_i, pot_kw=pot_inv, tensao=tensao,
            ),
        )

    return out


def apply_diagrama_bloco_tokens(out: dict[str, str]) -> dict[str, str]:
    """Textos do diagrama de bloco (planta DXF/DWG)."""
    qtd_m = out.get('QTD_MODULOS_2D') or _pad2(out.get('QTD_MODULOS'))
    pot_wp = str(out.get('POTENCIA_MODULO') or '').strip()
    fab_m = str(out.get('FABRICANTE_MODULO') or '').strip()
    mod_m = str(out.get('MODELO_MODULO') or '').strip()
    pw_n = _num(out.get('POTENCIA_MODULO'))
    if pw_n is not None:
        pot_unit_kwp = f'{pw_n / 1000:.2f}'.replace('.', ',')
    else:
        pot_unit_kwp = str(out.get('POTENCIA_MODULO_KWP') or '').strip()
    if qtd_m and pot_wp:
        marca = fab_m or mod_m
        out.setdefault(
            'TEXTO_DIAGRAMA_MODULOS',
            f'{qtd_m} x Módulos Fotovoltaicos de {pot_wp} Wp, marca {marca} '
            f'POT UNIT: {pot_unit_kwp} KW',
        )

    qtd_i = out.get('QTD_INVERSORES_2D') or _pad2(out.get('QTD_INVERSORES'))
    tipo = str(out.get('TIPO_EQUIPAMENTO_INVERSOR') or 'Inversor').strip()
    fab_i = str(out.get('FABRICANTE_INVERSOR') or '').strip()
    mod_i = str(out.get('MODELO_INVERSOR') or '').strip()
    if qtd_i:
        nome_inv = ' '.join(p for p in (fab_i, mod_i) if p).strip()
        out.setdefault(
            'TEXTO_DIAGRAMA_INVERSOR',
            f'{qtd_i} - {tipo} {nome_inv}'.strip(),
        )

    disj_inv = str(out.get('DISJUNTOR_CA_INVERSOR_A') or '').strip().upper().removesuffix('A')
    if disj_inv:
        out.setdefault('TEXTO_DISJUNTOR_CA_INVERSOR', f'Disjuntor {disj_inv}A')

    disj_pad = str(
        out.get('DISJUNTOR_CA_PADRAO_A') or out.get('DISJUNTOR_ENTRADA') or '40'
    ).strip().upper().removesuffix('A')
    out.setdefault('DISJUNTOR_CA_PADRAO_A', disj_pad)
    out.setdefault('TEXTO_DISJUNTOR_CA_PADRAO', f'Disjuntor {disj_pad}A')

    return out


def enrich_autocad_values(values: dict[str, str]) -> dict[str, str]:
    out = dict(values)

    if not out.get('DATA_DOCUMENTO'):
        out['DATA_DOCUMENTO'] = datetime.now().strftime('%d/%m/%Y')
    out.setdefault('DATA', out['DATA_DOCUMENTO'])

    qtd_m = _num(out.get('QTD_MODULOS'))
    pw = _num(out.get('POTENCIA_MODULO'))
    if qtd_m is not None and pw is not None:
        kwp_mod = qtd_m * pw / 1000
        out.setdefault('POTENCIA_TOTAL_INSTALADA', _fmt_br(kwp_mod, 2))
        out.setdefault('POTENCIA_PAINEL_KWP', _fmt_br(kwp_mod, 2))
    if pw is not None:
        out.setdefault('POTENCIA_MODULO_KWP', _fmt_br(pw / 1000, 3))

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

    apply_diagrama_bloco_tokens(out)
    apply_unifilar_tokens(out)
    apply_padrao_unifilar_tokens(out)

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
