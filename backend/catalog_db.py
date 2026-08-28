"""
Catálogo local SQLite — módulos, inversores e padrões de entrada reutilizáveis.
Consultado antes da IA; dados enriquecidos pela IA podem ser salvos para reuse.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'data' / 'catalog.db'

MODULE_FIELDS = (
    'fabricante', 'modelo', 'potencia_wp', 'voc', 'isc', 'vmpp', 'impp',
    'eficiencia', 'notas',
)
INVERTER_FIELDS = (
    'fabricante', 'modelo', 'potencia_kw', 'tipo_inversor', 'num_mppt',
    'mppt_min', 'mppt_max', 'tensao_nominal', 'corrente_nominal', 'eficiencia', 'notas',
)
PADRAO_FIELDS = (
    'uf', 'tipo_ligacao', 'tensao_v', 'disjuntor_a', 'bitola_cabo_mm2',
    'dps_tipo', 'curva_disjuntor', 'dr_ma', 'notas',
)

SEED_MODULES = [
    ('Jinko', 'JKM555M-72HL4-V', 555, 49.72, 14.03, 40.99, 13.55, 21.5, 'Módulo residencial comum'),
    ('Canadian Solar', 'HiKu6 CS6R-555MS', 555, 49.8, 14.0, 41.2, 13.5, 21.4, 'HiKu6 555 Wp'),
    ('Trina Solar', 'Vertex S TSM-450DE09.08', 450, 41.6, 13.9, 34.9, 12.9, 21.1, 'Vertex S residencial'),
    ('JA Solar', 'JAM72S30-555/MR', 555, 49.65, 14.02, 41.25, 13.45, 21.3, 'DeepBlue 3.0'),
    ('Longi', 'LR5-72HIH-555M', 555, 49.5, 14.0, 41.1, 13.5, 21.5, 'Hi-MO 5'),
    ('Risen', 'RSM110-8-555M', 555, 49.8, 14.05, 41.3, 13.44, 21.2, 'RSM110 série'),
    ('Jinko', 'JKM580N-72HL4-BDV', 580, 51.2, 14.35, 42.5, 13.65, 22.0, 'Tiger Neo 580 Wp'),
]
SEED_INVERTERS = [
    ('Growatt', 'MIN 5000TL-X', 5.0, 'STRING', 2, 80, 550, 220, 22.7, 97.6, 'Residencial string'),
    ('Growatt', 'MIN 8000TL-X', 8.0, 'STRING', 2, 80, 550, 220, 36.4, 97.8, 'String 8 kW mono'),
    ('APsystems', 'DS3D', 0.88, 'MICRO', 1, 16, 60, 220, 4.0, 96.5, 'Microinversor dual'),
    ('Deye', 'SUN-8K-SG05LP3', 8.0, 'STRING', 2, 150, 500, 220, 36.4, 97.8, 'Híbrido trifásico'),
    ('Fronius', 'Primo 5.0-1', 5.0, 'STRING', 2, 80, 1000, 230, 21.7, 97.0, 'Primo mono 5 kW'),
    ('Sungrow', 'SG5.0RS', 5.0, 'STRING', 2, 40, 530, 230, 21.7, 97.8, 'Residencial SG5'),
    ('Huawei', 'SUN2000-6KTL-L1', 6.0, 'STRING', 2, 90, 600, 230, 26.1, 98.2, 'Fusion Solar 6 kW'),
    ('Hoymiles', 'HM-800', 0.8, 'MICRO', 1, 16, 60, 230, 3.5, 96.7, 'Micro 800 W'),
]
SEED_PADRAO = [
    ('GO', 'MONOFASICO', '220V', 40, '10 mm²', 'DPS Classe II', 'C', 30, 'Residencial GO'),
    ('GO', 'TRIFASICO', '220/380V', 63, '10 mm²', 'DPS Classe II', 'C', 30, 'Trifásico GO — 380 V LL'),
    ('DEFAULT', 'MONOFASICO', '220V', 40, '10 mm²', 'DPS Classe II', 'C', 30, 'Padrão nacional'),
]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
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
                notas TEXT,
                updated_at TEXT,
                UNIQUE(fabricante, modelo)
            );
            CREATE TABLE IF NOT EXISTS catalog_inverters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fabricante TEXT NOT NULL,
                modelo TEXT NOT NULL,
                potencia_kw REAL,
                tipo_inversor TEXT,
                num_mppt INTEGER,
                mppt_min REAL, mppt_max REAL,
                tensao_nominal REAL, corrente_nominal REAL,
                eficiencia REAL,
                notas TEXT,
                updated_at TEXT,
                UNIQUE(fabricante, modelo)
            );
            CREATE TABLE IF NOT EXISTS catalog_padrao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uf TEXT NOT NULL,
                tipo_ligacao TEXT NOT NULL,
                tensao_v TEXT,
                disjuntor_a INTEGER,
                bitola_cabo_mm2 TEXT,
                dps_tipo TEXT,
                curva_disjuntor TEXT,
                dr_ma INTEGER,
                notas TEXT,
                updated_at TEXT,
                UNIQUE(uf, tipo_ligacao)
            );
            """
        )
        for row in SEED_MODULES:
            conn.execute(
                """
                INSERT OR IGNORE INTO catalog_modules
                (fabricante, modelo, potencia_wp, voc, isc, vmpp, impp, eficiencia, notas, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*row, _now()),
            )
        for row in SEED_INVERTERS:
            conn.execute(
                """
                INSERT OR IGNORE INTO catalog_inverters
                (fabricante, modelo, potencia_kw, tipo_inversor, num_mppt, mppt_min, mppt_max,
                 tensao_nominal, corrente_nominal, eficiencia, notas, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*row, _now()),
            )
        for row in SEED_PADRAO:
            conn.execute(
                """
                INSERT OR IGNORE INTO catalog_padrao
                (uf, tipo_ligacao, tensao_v, disjuntor_a, bitola_cabo_mm2, dps_tipo,
                 curva_disjuntor, dr_ma, notas, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*row, _now()),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(s: str | None) -> str:
    return (s or '').strip().lower()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def lookup_module(fabricante: str, modelo: str) -> dict | None:
    init_db()
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM catalog_modules').fetchall()
        fab, mod = _norm(fabricante), _norm(modelo)
        for row in rows:
            if _norm(row['fabricante']) == fab and _norm(row['modelo']) == mod:
                return _row_to_dict(row)
            if mod and mod in _norm(row['modelo']):
                if not fab or fab in _norm(row['fabricante']):
                    return _row_to_dict(row)
    return None


def lookup_inverter(fabricante: str, modelo: str) -> dict | None:
    init_db()
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM catalog_inverters').fetchall()
        fab, mod = _norm(fabricante), _norm(modelo)
        for row in rows:
            if _norm(row['fabricante']) == fab and _norm(row['modelo']) == mod:
                return _row_to_dict(row)
            if mod and mod in _norm(row['modelo']):
                if not fab or fab in _norm(row['fabricante']):
                    return _row_to_dict(row)
    return None


def lookup_padrao(uf: str, tipo_ligacao: str) -> dict | None:
    init_db()
    uf_key = (uf or 'DEFAULT').upper()[:2]
    tipo = (tipo_ligacao or 'MONOFASICO').upper()
    with _connect() as conn:
        row = conn.execute(
            'SELECT * FROM catalog_padrao WHERE uf = ? AND tipo_ligacao = ?',
            (uf_key, tipo),
        ).fetchone()
        if row:
            return _row_to_dict(row)
        row = conn.execute(
            'SELECT * FROM catalog_padrao WHERE uf = ? AND tipo_ligacao = ?',
            ('DEFAULT', tipo),
        ).fetchone()
        return _row_to_dict(row)


def catalog_module_to_specs(row: dict) -> dict:
    return {
        'potencia': row.get('potencia_wp'),
        'voc': row.get('voc'),
        'isc': row.get('isc'),
        'vmpp': row.get('vmpp'),
        'impp': row.get('impp'),
        'eficiencia': row.get('eficiencia'),
    }


def catalog_inverter_to_specs(row: dict) -> dict:
    return {
        'potencia': row.get('potencia_kw'),
        'tipo_inversor': row.get('tipo_inversor'),
        'num_mppt': row.get('num_mppt'),
        'mppt_min': row.get('mppt_min'),
        'mppt_max': row.get('mppt_max'),
        'tensao_nominal': row.get('tensao_nominal'),
        'corrente_nominal': row.get('corrente_nominal'),
        'eficiencia': row.get('eficiencia'),
    }


def list_table(table: str) -> list[dict]:
    init_db()
    allowed = {
        'modules': 'catalog_modules',
        'inverters': 'catalog_inverters',
        'padrao': 'catalog_padrao',
    }
    sql_table = allowed.get(table)
    if not sql_table:
        raise ValueError('Tabela inválida')
    with _connect() as conn:
        rows = conn.execute(f'SELECT * FROM {sql_table} ORDER BY id').fetchall()
        return [dict(r) for r in rows]


def upsert_row(table: str, data: dict) -> dict:
    init_db()
    mapping = {
        'modules': ('catalog_modules', MODULE_FIELDS, ('fabricante', 'modelo')),
        'inverters': ('catalog_inverters', INVERTER_FIELDS, ('fabricante', 'modelo')),
        'padrao': ('catalog_padrao', PADRAO_FIELDS, ('uf', 'tipo_ligacao')),
    }
    sql_table, fields, conflict = mapping[table]
    payload = {f: data.get(f) for f in fields}
    if not all(payload.get(k) for k in conflict):
        raise ValueError(f'Campos obrigatórios: {conflict}')
    cols = list(fields) + ['updated_at']
    vals = [payload[f] for f in fields] + [_now()]
    placeholders = ', '.join('?' * len(cols))
    set_clause = ', '.join(f'{f}=excluded.{f}' for f in fields) + ', updated_at=excluded.updated_at'
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {sql_table} ({', '.join(cols)})
            VALUES ({placeholders})
            ON CONFLICT({', '.join(conflict)}) DO UPDATE SET {set_clause}
            """,
            vals,
        )
        row = conn.execute(
            f"SELECT * FROM {sql_table} WHERE {' AND '.join(f'{k}=?' for k in conflict)}",
            [payload[k] for k in conflict],
        ).fetchone()
        return dict(row)


def delete_row(table: str, row_id: int) -> bool:
    init_db()
    sql_table = {
        'modules': 'catalog_modules',
        'inverters': 'catalog_inverters',
        'padrao': 'catalog_padrao',
    }[table]
    with _connect() as conn:
        cur = conn.execute(f'DELETE FROM {sql_table} WHERE id = ?', (row_id,))
        return cur.rowcount > 0


def save_module_from_form(fabricante: str, modelo: str, specs: dict) -> None:
    if not fabricante or not modelo:
        return
    upsert_row('modules', {
        'fabricante': fabricante,
        'modelo': modelo,
        'potencia_wp': specs.get('potencia') or specs.get('power'),
        'voc': specs.get('voc'),
        'isc': specs.get('isc'),
        'vmpp': specs.get('vmpp'),
        'impp': specs.get('impp'),
        'eficiencia': specs.get('eficiencia'),
        'notas': specs.get('notas') or 'Importado do projeto',
    })


def save_inverter_from_form(fabricante: str, modelo: str, specs: dict) -> None:
    if not fabricante or not modelo:
        return
    upsert_row('inverters', {
        'fabricante': fabricante,
        'modelo': modelo,
        'potencia_kw': specs.get('potencia') or specs.get('power'),
        'tipo_inversor': specs.get('tipo_inversor'),
        'num_mppt': specs.get('num_mppt'),
        'mppt_min': specs.get('mppt_min'),
        'mppt_max': specs.get('mppt_max'),
        'tensao_nominal': specs.get('tensao_nominal'),
        'corrente_nominal': specs.get('corrente_nominal'),
        'eficiencia': specs.get('eficiencia'),
        'notas': specs.get('notas') or 'Importado do projeto',
    })
