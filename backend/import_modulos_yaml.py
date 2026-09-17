"""
Importa modulos_solares.yaml → catálogo SQLite (catalog_modules).
Fonte: dados/modulos_solares.yaml ou obsoleto/Yamlmodulos.yaml
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATHS = (
    ROOT / 'dados' / 'modulos_solares.yaml',
    ROOT / 'obsoleto' / 'Yamlmodulos.yaml',
)


def _parse_dimensoes_mm(value: str | None) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    parts = re.split(r'[xX×]', str(value).strip())
    if len(parts) < 2:
        return None, None
    try:
        comprimento = round(float(parts[0]) / 1000, 4)
        largura = round(float(parts[1]) / 1000, 4)
        return comprimento, largura
    except (TypeError, ValueError):
        return None, None


def _build_modelo(marca: str, potencia_w: float | int, tecnologia: str = '') -> str:
    pot = int(potencia_w) if potencia_w else 0
    tech = (tecnologia or '').strip()
    if tech:
        return f'{pot}W {tech}'
    return f'{pot}W'


def yaml_entry_to_catalog(entry: dict[str, Any]) -> dict[str, Any]:
    marca = (entry.get('marca') or entry.get('fabricante') or '').strip()
    potencia = entry.get('potencia_w') or entry.get('potencia_wp') or entry.get('potencia')
    tecnologia = (entry.get('tecnologia') or '').strip()
    comprimento, largura = _parse_dimensoes_mm(entry.get('dimensoes_mm'))

    if not comprimento and entry.get('comprimento_m'):
        comprimento = entry.get('comprimento_m')
    if not largura and entry.get('largura_m'):
        largura = entry.get('largura_m')

    notas_parts = []
    if tecnologia:
        notas_parts.append(tecnologia)
    if entry.get('dimensoes_mm'):
        notas_parts.append(f"Dim: {entry['dimensoes_mm']} mm")
    notas_parts.append('Importado de modulos_solares.yaml')

    return {
        'fabricante': marca,
        'modelo': _build_modelo(marca, potencia, tecnologia),
        'potencia_wp': potencia,
        'voc': entry.get('voc_v') or entry.get('voc'),
        'isc': entry.get('isc_a') or entry.get('isc'),
        'vmpp': entry.get('vmp_v') or entry.get('vmpp'),
        'impp': entry.get('imp_a') or entry.get('impp'),
        'eficiencia': entry.get('eficiencia_pct') or entry.get('eficiencia'),
        'comprimento_m': comprimento,
        'largura_m': largura,
        'peso_kg': entry.get('peso_kg'),
        'notas': ' — '.join(notas_parts),
    }


def parse_modulos_yaml_data(data: Any) -> list[dict[str, Any]]:
    """Aceita dict com lista, lista pura ou um único módulo."""
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get('modulos_solares') or data.get('modulos')
        if entries is None and (data.get('marca') or data.get('fabricante') or data.get('potencia_w')):
            entries = [data]
        entries = entries or []
    else:
        raise ValueError('YAML inválido — cole um módulo, uma lista ou { modulos_solares: [...] }')

    if not isinstance(entries, list):
        raise ValueError('Lista de módulos ausente ou inválida')

    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Preferir modelo comercial no catálogo quando existir
        catalog_row = yaml_entry_to_catalog(entry)
        modelo_com = (entry.get('modelo_comercial') or entry.get('modelo') or '').strip()
        if modelo_com:
            catalog_row['modelo'] = modelo_com
        if catalog_row['fabricante'] and catalog_row['potencia_wp']:
            result.append(catalog_row)
    return result


def load_yaml_modulos_from_text(text: str) -> list[dict[str, Any]]:
    data = yaml.safe_load(text or '')
    return parse_modulos_yaml_data(data)


def load_yaml_modulos(path: Path | None = None) -> list[dict[str, Any]]:
    yaml_path = path
    if yaml_path is None:
        for candidate in YAML_PATHS:
            if candidate.is_file():
                yaml_path = candidate
                break
    if yaml_path is None or not yaml_path.is_file():
        raise FileNotFoundError(
            'Arquivo de módulos não encontrado. Coloque modulos_solares.yaml em dados/ '
            'ou Yamlmodulos.yaml em obsoleto/.'
        )

    data = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
    return parse_modulos_yaml_data(data)


def _upsert_modulos_rows(rows: list[dict[str, Any]], *, source: str | None = None) -> dict[str, Any]:
    from catalog_db import MODULE_FIELDS, _connect, _now, init_db

    imported = 0
    errors: list[str] = []
    fields = list(MODULE_FIELDS)
    cols = fields + ['updated_at']
    set_clause = ', '.join(f'{f}=excluded.{f}' for f in fields) + ', updated_at=excluded.updated_at'
    placeholders = ', '.join('?' * len(cols))

    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fabricante TEXT NOT NULL,
                modelo TEXT NOT NULL,
                potencia_wp REAL,
                voc REAL, isc REAL, vmpp REAL, impp REAL,
                eficiencia REAL,
                comprimento_m REAL, largura_m REAL, peso_kg REAL,
                notas TEXT,
                updated_at TEXT,
                UNIQUE(fabricante, modelo)
            );
            """
        )
        for row in rows:
            try:
                payload = {f: row.get(f) for f in fields}
                if not payload.get('fabricante') or not payload.get('modelo'):
                    raise ValueError('fabricante e modelo obrigatórios')
                vals = [payload[f] for f in fields] + [_now()]
                conn.execute(
                    f"""
                    INSERT INTO catalog_modules ({', '.join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT(fabricante, modelo) DO UPDATE SET {set_clause}
                    """,
                    vals,
                )
                imported += 1
            except Exception as exc:
                errors.append(f"{row.get('fabricante')} {row.get('modelo')}: {exc}")
        conn.commit()

    try:
        init_db()
    except Exception:
        pass

    return {
        'success': len(errors) == 0,
        'source': source,
        'imported': imported,
        'total_in_yaml': len(rows),
        'errors': errors,
        'modules': rows,
    }


def append_modulos_yaml_file(raw_entries: list[dict[str, Any]], path: Path | None = None) -> str:
    """Acrescenta entradas ao YAML em disco (dados/modulos_solares.yaml)."""
    yaml_path = path or resolve_yaml_path() or YAML_PATHS[0]
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    if yaml_path.is_file():
        data = yaml.safe_load(yaml_path.read_text(encoding='utf-8')) or {}
        if not isinstance(data, dict):
            data = {'modulos_solares': []}
    else:
        data = {'modulos_solares': []}
    lista = data.get('modulos_solares')
    if not isinstance(lista, list):
        lista = []
        data['modulos_solares'] = lista
    lista.extend(raw_entries)
    yaml_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding='utf-8',
    )
    return str(yaml_path)


def import_modulos_yaml_text(text: str, *, save_file: bool = True) -> dict[str, Any]:
    """Cola YAML → SQLite; opcionalmente grava/acrescenta em dados/modulos_solares.yaml."""
    data = yaml.safe_load(text or '')
    rows = parse_modulos_yaml_data(data)
    if not rows:
        raise ValueError('Nenhum módulo válido encontrado no YAML colado.')

    # Entradas brutas para o arquivo (preserva campos do datasheet)
    if isinstance(data, list):
        raw_entries = [e for e in data if isinstance(e, dict)]
    elif isinstance(data, dict):
        raw_entries = data.get('modulos_solares') or data.get('modulos')
        if raw_entries is None and (data.get('marca') or data.get('fabricante')):
            raw_entries = [data]
        raw_entries = [e for e in (raw_entries or []) if isinstance(e, dict)]
    else:
        raw_entries = []

    saved_path = None
    if save_file and raw_entries:
        saved_path = append_modulos_yaml_file(raw_entries)

    result = _upsert_modulos_rows(rows, source=saved_path or 'paste')
    result['saved_path'] = saved_path
    return result


def import_modulos_yaml(path: Path | None = None) -> dict[str, Any]:
    """Upsert de todos os módulos do YAML no SQLite. Retorna estatísticas."""
    yaml_path = path
    if yaml_path is None:
        for candidate in YAML_PATHS:
            if candidate.is_file():
                yaml_path = candidate
                break

    rows = load_yaml_modulos(yaml_path)
    return _upsert_modulos_rows(rows, source=str(yaml_path) if yaml_path else None)


def resolve_yaml_path() -> Path | None:
    for candidate in YAML_PATHS:
        if candidate.is_file():
            return candidate
    return None


if __name__ == '__main__':
    result = import_modulos_yaml()
    print(f"Importados: {result['imported']}/{result['total_in_yaml']} de {result['source']}")
    if result['errors']:
        for err in result['errors']:
            print('ERRO:', err)
