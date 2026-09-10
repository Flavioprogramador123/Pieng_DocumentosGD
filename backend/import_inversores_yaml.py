"""
Importa inversores.yaml → catálogo SQLite (catalog_inverters).
Fonte: dados/inversores.yaml ou obsoleto/Yamlinversores.yaml
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATHS = (
    ROOT / 'dados' / 'inversores.yaml',
    ROOT / 'obsoleto' / 'Yamlinversores.yaml',
)


def _nums(text: str | None) -> list[float]:
    if text is None:
        return []
    return [float(x.replace(',', '.')) for x in re.findall(r'[\d.]+', str(text))]


def _first_num(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    nums = _nums(str(val))
    return nums[0] if nums else None


def _range_min_max(val: Any) -> tuple[float | None, float | None]:
    if isinstance(val, (int, float)):
        v = float(val)
        return v, v
    nums = _nums(str(val))
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _max_num(val: Any) -> float | None:
    _, hi = _range_min_max(val)
    return hi


def _parse_tensao_ca(val: Any) -> tuple[float | None, float | None, float | None]:
    """Ex.: '220 / 187 - 253' → nominal, min, max."""
    if val is None:
        return None, None, None
    text = str(val)
    if '/' in text:
        left, right = text.split('/', 1)
        nominal = _first_num(left)
        lo, hi = _range_min_max(right)
        return nominal, lo, hi
    lo, hi = _range_min_max(text)
    return lo, lo, hi


def _map_tipo_inversor(tipo: str | None) -> str:
    t = (tipo or '').lower()
    if 'micro' in t:
        return 'MICRO'
    if 'híbr' in t or 'hibr' in t or 'hybrid' in t:
        return 'HIBRIDO'
    return 'STRING'


def _potencia_kw_from_modelo(modelo: str, potencia_w: float | None) -> float | None:
    if potencia_w:
        return round(potencia_w / 1000, 3)
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*KW', modelo.upper())
    if match:
        return float(match.group(1).replace(',', '.'))
    return None


def _infer_fase_ca(entry: dict[str, Any], potencia_kw: float | None) -> str:
    tipo = (entry.get('tipo') or entry.get('tipo_inversor') or '').upper()
    if 'MICRO' in tipo:
        return 'MONOFASICO'
    explicit = (entry.get('fase_ca') or entry.get('fase') or '').upper()
    if explicit in ('MONOFASICO', 'MONO', 'MONOFÁSICO'):
        return 'MONOFASICO'
    if explicit in ('TRIFASICO', 'TRI', 'TRIFÁSICO'):
        return 'TRIFASICO'
    if potencia_kw is not None:
        if potencia_kw >= 12:
            return 'TRIFASICO'
        if potencia_kw <= 10:
            return 'MONOFASICO'
    return 'MONOFASICO'


def _json_list(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        return json.dumps(val)
    return None


def yaml_entry_to_catalog(entry: dict[str, Any]) -> dict[str, Any]:
    cc = entry.get('entrada_cc') or {}
    ca = entry.get('saida_ca') or {}
    perf = entry.get('performance') or {}

    fabricante = (entry.get('fabricante') or '').strip()
    modelo = (entry.get('modelo') or '').strip()
    tipo_raw = entry.get('tipo') or ''

    mppt_lo, mppt_hi = _range_min_max(cc.get('tensao_rastreamento_mppt_v'))
    oper_lo, _ = _range_min_max(cc.get('faixa_tensao_operacao_v'))
    tensao_nom, tensao_min, tensao_max = _parse_tensao_ca(ca.get('tensao_ca_nominal_faixa_v'))

    pot_saida_w = _first_num(ca.get('potencia_max_saida_w'))
    pot_cc_wp = _max_num(cc.get('potencia_max_arranjo_wp'))

    potencia_kw = _potencia_kw_from_modelo(modelo, pot_saida_w)

    strings_arr = cc.get('strings_por_mppt')
    if isinstance(strings_arr, list):
        qtd_strings_max = sum(max(1, int(x)) for x in strings_arr)
    else:
        qtd_strings_max = cc.get('numero_mppts') or cc.get('num_mppt')

    icc_raw = cc.get('corrente_entrada_cc_max_a_por_mppt')
    icc_json = _json_list(icc_raw)
    strings_json = _json_list(strings_arr)
    micros_max = cc.get('micros_max_por_disjuntor_ca') or cc.get('micros_max_disjuntor_ca')
    fase_ca = _infer_fase_ca(entry, potencia_kw)

    notas_parts = [tipo_raw] if tipo_raw else []
    if perf.get('grau_protecao'):
        notas_parts.append(str(perf['grau_protecao']))
    if perf.get('garantia_anos'):
        notas_parts.append(f"Garantia {perf['garantia_anos']} anos")
    notas_parts.append('Importado de inversores.yaml')

    thd = _first_num(ca.get('thd_corrente_pct'))
    fp = _first_num(ca.get('fator_potencia'))
    freq = _first_num(ca.get('frequencia_nominal_faixa_hz'))

    return {
        'fabricante': fabricante,
        'modelo': modelo,
        'potencia_kw': potencia_kw,
        'tipo_inversor': _map_tipo_inversor(tipo_raw),
        'fase_ca': fase_ca,
        'num_mppt': cc.get('numero_mppts') or cc.get('num_mppt'),
        'mppt_min': mppt_lo,
        'mppt_max': mppt_hi,
        'tensao_nominal': tensao_nom,
        'corrente_nominal': _first_num(ca.get('corrente_saida_max_a')),
        'eficiencia': perf.get('eficiencia_pico_pct') or perf.get('eficiencia'),
        'corrente_max_cc': _first_num(cc.get('corrente_entrada_cc_max_a')),
        'tensao_max_cc': _first_num(cc.get('tensao_entrada_max_v')),
        'potencia_max_cc_kw': round(pot_cc_wp / 1000, 2) if pot_cc_wp else None,
        'potencia_max_saida_ca_kw': round(pot_saida_w / 1000, 2) if pot_saida_w else None,
        'corrente_max_saida_ca': _first_num(ca.get('corrente_saida_max_a')),
        'tensao_min_ca': tensao_min,
        'tensao_max_ca': tensao_max,
        'thd_pct': thd,
        'fator_potencia': fp if fp is not None else 0.99,
        'frequencia_hz': freq if freq is not None else 60,
        'tensao_partida_cc': oper_lo or mppt_lo,
        'qtd_strings_max': qtd_strings_max,
        'strings_por_mppt_json': strings_json,
        'icc_mppt_json': icc_json,
        'micros_max_disjuntor_ca': int(micros_max) if micros_max else None,
        'notas': ' — '.join(notas_parts),
    }


def load_yaml_inversores(path: Path | None = None) -> list[dict[str, Any]]:
    yaml_path = path
    if yaml_path is None:
        for candidate in YAML_PATHS:
            if candidate.is_file():
                yaml_path = candidate
                break
    if yaml_path is None or not yaml_path.is_file():
        raise FileNotFoundError(
            'Arquivo de inversores não encontrado. Coloque inversores.yaml em dados/ '
            'ou Yamlinversores.yaml em obsoleto/.'
        )

    data = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('YAML inválido — esperado objeto com inversores')

    entries = data.get('inversores') or []
    if not isinstance(entries, list):
        raise ValueError('Lista inversores ausente ou inválida')

    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        row = yaml_entry_to_catalog(entry)
        if row['fabricante'] and row['modelo']:
            result.append(row)
    return result


def import_inversores_yaml(path: Path | None = None) -> dict[str, Any]:
    """Upsert de todos os inversores do YAML no SQLite."""
    from catalog_db import INVERTER_FIELDS, _connect, _migrate_schema, _now

    yaml_path = path
    if yaml_path is None:
        for candidate in YAML_PATHS:
            if candidate.is_file():
                yaml_path = candidate
                break

    rows = load_yaml_inversores(yaml_path)
    imported = 0
    errors: list[str] = []
    fields = list(INVERTER_FIELDS)
    cols = fields + ['updated_at']
    set_clause = ', '.join(f'{f}=excluded.{f}' for f in fields) + ', updated_at=excluded.updated_at'
    placeholders = ', '.join('?' * len(cols))

    with _connect() as conn:
        _migrate_schema(conn)
        for row in rows:
            try:
                payload = {f: row.get(f) for f in fields}
                if not payload.get('fabricante') or not payload.get('modelo'):
                    raise ValueError('fabricante e modelo obrigatórios')
                vals = [payload[f] for f in fields] + [_now()]
                conn.execute(
                    f"""
                    INSERT INTO catalog_inverters ({', '.join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT(fabricante, modelo) DO UPDATE SET {set_clause}
                    """,
                    vals,
                )
                imported += 1
            except Exception as exc:
                errors.append(f"{row.get('fabricante')} {row.get('modelo')}: {exc}")
        conn.commit()

    return {
        'success': len(errors) == 0,
        'source': str(yaml_path) if yaml_path else None,
        'imported': imported,
        'total_in_yaml': len(rows),
        'errors': errors,
        'inverters': rows,
    }


def resolve_yaml_path() -> Path | None:
    for candidate in YAML_PATHS:
        if candidate.is_file():
            return candidate
    return None


if __name__ == '__main__':
    result = import_inversores_yaml()
    print(f"Importados: {result['imported']}/{result['total_in_yaml']} de {result['source']}")
    if result['errors']:
        for err in result['errors']:
            print('ERRO:', err)
