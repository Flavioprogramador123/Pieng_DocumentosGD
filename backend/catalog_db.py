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

_db_initialized = False
_db_initializing = False

MODULE_FIELDS = (
    'fabricante', 'modelo', 'potencia_wp', 'voc', 'isc', 'vmpp', 'impp',
    'eficiencia', 'comprimento_m', 'largura_m', 'peso_kg', 'notas',
)
INVERTER_FIELDS = (
    'fabricante', 'modelo', 'potencia_kw', 'tipo_inversor', 'fase_ca', 'num_mppt',
    'mppt_min', 'mppt_max', 'tensao_nominal', 'corrente_nominal', 'eficiencia',
    'corrente_max_cc', 'tensao_max_cc', 'potencia_max_cc_kw',
    'potencia_max_saida_ca_kw', 'corrente_max_saida_ca',
    'tensao_min_ca', 'tensao_max_ca', 'thd_pct', 'fator_potencia',
    'frequencia_hz', 'tensao_partida_cc', 'qtd_strings_max',
    'strings_por_mppt_json', 'icc_mppt_json', 'micros_max_disjuntor_ca', 'notas',
)

# Match por potência: só ±2 Wp (evita usar specs de outro módulo, ex. 544→620).
MODULE_POWER_TOLERANCE_WP = 2
PADRAO_FIELDS = (
    'uf', 'tipo_ligacao', 'tensao_v', 'disjuntor_a', 'bitola_cabo_mm2',
    'dps_tipo', 'curva_disjuntor', 'dr_ma', 'notas',
)

SEED_MODULES = [
    ('Jinko', 'JKM555M-72HL4-V', 555, 49.72, 14.03, 40.99, 13.55, 21.5, 2.278, 1.134, 28.5, 'Módulo residencial comum'),
    ('Canadian Solar', 'HiKu6 CS6R-555MS', 555, 49.8, 14.0, 41.2, 13.5, 21.4, 2.278, 1.134, 28.0, 'HiKu6 555 Wp'),
    ('Trina Solar', 'Vertex S TSM-450DE09.08', 450, 41.6, 13.9, 34.9, 12.9, 21.1, 1.762, 1.134, 22.5, 'Vertex S residencial'),
    ('JA Solar', 'JAM72S30-555/MR', 555, 49.65, 14.02, 41.25, 13.45, 21.3, 2.278, 1.134, 28.2, 'DeepBlue 3.0'),
    ('Longi', 'LR5-72HIH-555M', 555, 49.5, 14.0, 41.1, 13.5, 21.5, 2.278, 1.134, 28.4, 'Hi-MO 5'),
    ('Risen', 'RSM110-8-555M', 555, 49.8, 14.05, 41.3, 13.44, 21.2, 2.278, 1.134, 28.0, 'RSM110 série'),
    ('Jinko', 'JKM580N-72HL4-BDV', 580, 51.2, 14.35, 42.5, 13.65, 22.0, 2.278, 1.134, 29.0, 'Tiger Neo 580 Wp'),
]
SEED_INVERTERS = [
    ('Growatt', 'MIN 5000TL-X', 5.0, 'STRING', 2, 80, 550, 230, 21.7, 97.6,
     13.0, 600, 6.5, 5.5, 23.9, 180, 270, 3.0, 0.99, 60, 80, 2, 'Residencial string'),
    ('Growatt', 'MIN 8000TL-X', 8.0, 'STRING', 2, 80, 550, 230, 36.4, 97.8,
     16.0, 600, 10.4, 8.8, 38.3, 180, 270, 3.0, 0.99, 60, 80, 2, 'String 8 kW mono'),
    ('APsystems', 'DS3D', 0.88, 'MICRO', 1, 16, 60, 230, 4.0, 96.5,
     14.0, 60, 1.2, 0.97, 4.2, 180, 270, 5.0, 0.99, 60, 16, 1, 'Microinversor dual'),
    ('Deye', 'SUN-8K-SG05LP3', 8.0, 'STRING', 2, 150, 500, 230, 36.4, 97.8,
     18.0, 500, 10.4, 8.8, 38.3, 180, 270, 3.0, 0.99, 60, 150, 2, 'Híbrido trifásico'),
    ('Fronius', 'Primo 5.0-1', 5.0, 'STRING', 2, 80, 1000, 230, 21.7, 97.0,
     12.0, 1000, 6.75, 5.0, 21.7, 180, 270, 3.0, 1.0, 60, 80, 2, 'Primo mono 5 kW'),
    ('Sungrow', 'SG5.0RS', 5.0, 'STRING', 2, 40, 530, 230, 21.7, 97.8,
     13.0, 600, 6.5, 5.5, 23.9, 180, 270, 3.0, 0.99, 60, 40, 2, 'Residencial SG5'),
    ('Huawei', 'SUN2000-6KTL-L1', 6.0, 'STRING', 2, 90, 600, 230, 26.1, 98.2,
     15.0, 600, 7.8, 6.6, 28.7, 180, 270, 3.0, 0.99, 60, 90, 2, 'Fusion Solar 6 kW'),
    ('Hoymiles', 'HM-800', 0.8, 'MICRO', 1, 16, 60, 230, 3.5, 96.7,
     12.0, 60, 1.1, 0.88, 3.8, 180, 270, 5.0, 0.99, 60, 16, 1, 'Micro 800 W'),
]
SEED_PADRAO = [
    ('GO', 'MONOFASICO', '220V', 40, '10 mm²', 'DPS Classe II', 'C', 30, 'Residencial GO'),
    ('GO', 'TRIFASICO', '220/380V', 63, '10 mm²', 'DPS Classe II', 'C', 30, 'Trifásico GO — 380 V LL'),
    ('DEFAULT', 'MONOFASICO', '220V', 40, '10 mm²', 'DPS Classe II', 'C', 30, 'Padrão nacional'),
]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    module_cols = [
        'comprimento_m REAL', 'largura_m REAL', 'peso_kg REAL',
    ]
    inverter_cols = [
        'corrente_max_cc REAL', 'tensao_max_cc REAL', 'potencia_max_cc_kw REAL',
        'potencia_max_saida_ca_kw REAL', 'corrente_max_saida_ca REAL',
        'tensao_min_ca REAL', 'tensao_max_ca REAL', 'thd_pct REAL',
        'fator_potencia REAL', 'frequencia_hz REAL', 'tensao_partida_cc REAL',
        'qtd_strings_max INTEGER',
        'fase_ca TEXT', 'strings_por_mppt_json TEXT', 'icc_mppt_json TEXT',
        'micros_max_disjuntor_ca INTEGER',
    ]
    for col in module_cols:
        try:
            conn.execute(f'ALTER TABLE catalog_modules ADD COLUMN {col}')
        except sqlite3.OperationalError:
            pass
    for col in inverter_cols:
        try:
            conn.execute(f'ALTER TABLE catalog_inverters ADD COLUMN {col}')
        except sqlite3.OperationalError:
            pass


def init_db() -> None:
    global _db_initialized, _db_initializing
    if _db_initialized:
        return
    if _db_initializing:
        return

    _db_initializing = True
    try:
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
                corrente_max_cc REAL, tensao_max_cc REAL, potencia_max_cc_kw REAL,
                potencia_max_saida_ca_kw REAL, corrente_max_saida_ca REAL,
                tensao_min_ca REAL, tensao_max_ca REAL, thd_pct REAL,
                fator_potencia REAL, frequencia_hz REAL, tensao_partida_cc REAL,
                qtd_strings_max INTEGER,
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
            _migrate_schema(conn)
            mod_set = (
                'potencia_wp=excluded.potencia_wp, voc=excluded.voc, isc=excluded.isc, '
                'vmpp=excluded.vmpp, impp=excluded.impp, eficiencia=excluded.eficiencia, '
                'comprimento_m=excluded.comprimento_m, largura_m=excluded.largura_m, '
                'peso_kg=excluded.peso_kg, notas=excluded.notas, updated_at=excluded.updated_at'
            )
            for row in SEED_MODULES:
                conn.execute(
                    f"""
                    INSERT INTO catalog_modules
                    (fabricante, modelo, potencia_wp, voc, isc, vmpp, impp, eficiencia,
                     comprimento_m, largura_m, peso_kg, notas, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fabricante, modelo) DO UPDATE SET {mod_set}
                    """,
                    (*row, _now()),
                )
            inv_set = (
                'potencia_kw=excluded.potencia_kw, tipo_inversor=excluded.tipo_inversor, '
                'fase_ca=excluded.fase_ca, num_mppt=excluded.num_mppt, mppt_min=excluded.mppt_min, '
                'mppt_max=excluded.mppt_max, tensao_nominal=excluded.tensao_nominal, '
                'corrente_nominal=excluded.corrente_nominal, eficiencia=excluded.eficiencia, '
                'corrente_max_cc=excluded.corrente_max_cc, tensao_max_cc=excluded.tensao_max_cc, '
                'potencia_max_cc_kw=excluded.potencia_max_cc_kw, '
                'potencia_max_saida_ca_kw=excluded.potencia_max_saida_ca_kw, '
                'corrente_max_saida_ca=excluded.corrente_max_saida_ca, '
                'tensao_min_ca=excluded.tensao_min_ca, tensao_max_ca=excluded.tensao_max_ca, '
                'thd_pct=excluded.thd_pct, fator_potencia=excluded.fator_potencia, '
                'frequencia_hz=excluded.frequencia_hz, tensao_partida_cc=excluded.tensao_partida_cc, '
                'qtd_strings_max=excluded.qtd_strings_max, '
                'strings_por_mppt_json=excluded.strings_por_mppt_json, '
                'icc_mppt_json=excluded.icc_mppt_json, '
                'micros_max_disjuntor_ca=excluded.micros_max_disjuntor_ca, '
                'notas=excluded.notas, updated_at=excluded.updated_at'
            )
            for row in SEED_INVERTERS:
                conn.execute(
                    f"""
                    INSERT INTO catalog_inverters
                    (fabricante, modelo, potencia_kw, tipo_inversor, num_mppt, mppt_min, mppt_max,
                     tensao_nominal, corrente_nominal, eficiencia, corrente_max_cc, tensao_max_cc,
                     potencia_max_cc_kw, potencia_max_saida_ca_kw, corrente_max_saida_ca,
                     tensao_min_ca, tensao_max_ca, thd_pct, fator_potencia, frequencia_hz,
                     tensao_partida_cc, qtd_strings_max, notas, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fabricante, modelo) DO UPDATE SET {inv_set}
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
            try:
                from normas_loader import iter_padrao_seed_rows
                for row in iter_padrao_seed_rows():
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO catalog_padrao
                        (uf, tipo_ligacao, tensao_v, disjuntor_a, bitola_cabo_mm2, dps_tipo,
                         curva_disjuntor, dr_ma, notas, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (*row, _now()),
                    )
            except Exception:
                pass
    finally:
        _db_initializing = False

    _db_initialized = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(s: str | None) -> str:
    return (s or '').strip().lower()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def _parse_potencia(val: Any) -> float | None:
    if val is None or str(val).strip() == '':
        return None
    try:
        return float(str(val).replace(',', '.').replace('Wp', '').replace('W', '').strip())
    except (TypeError, ValueError):
        return None


def lookup_module(
    fabricante: str,
    modelo: str,
    potencia_wp: float | int | str | None = None,
) -> dict | None:
    init_db()
    fab, mod = _norm(fabricante), _norm(modelo)
    pot_target = _parse_potencia(potencia_wp)

    with _connect() as conn:
        rows = conn.execute('SELECT * FROM catalog_modules').fetchall()

        # 1) fabricante + modelo exato ou parcial
        for row in rows:
            if _norm(row['fabricante']) == fab and _norm(row['modelo']) == mod:
                return _row_to_dict(row)
            if mod and mod in _norm(row['modelo']):
                if not fab or fab in _norm(row['fabricante']):
                    return _row_to_dict(row)

        # 2) modelo contém potência (ex.: "620W Bifacial")
        if mod:
            for row in rows:
                row_mod = _norm(row['modelo'])
                if mod in row_mod or row_mod in mod:
                    if not fab or fab in _norm(row['fabricante']):
                        return _row_to_dict(row)

        # 3) fabricante + potência (Yamlmodulos — ex.: RENE PV 620W)
        if fab and pot_target is not None:
            best = None
            best_delta = float('inf')
            for row in rows:
                if fab not in _norm(row['fabricante']) and _norm(row['fabricante']) not in fab:
                    continue
                row_pot = _parse_potencia(row['potencia_wp'])
                if row_pot is None:
                    continue
                delta = abs(row_pot - pot_target)
                if delta < best_delta:
                    best_delta = delta
                    best = row
            if best is not None and best_delta <= MODULE_POWER_TOLERANCE_WP:
                return _row_to_dict(best)

        # 4) só potência (fabricante vazio no formulário)
        if pot_target is not None and not fab:
            for row in rows:
                row_pot = _parse_potencia(row['potencia_wp'])
                if row_pot is not None and abs(row_pot - pot_target) <= 1:
                    return _row_to_dict(row)

    return None


def lookup_inverter(
    fabricante: str,
    modelo: str,
    potencia_kw: float | int | str | None = None,
) -> dict | None:
    init_db()
    fab, mod = _norm(fabricante), _norm(modelo)
    pot_target = _parse_potencia(potencia_kw)
    if pot_target is not None and pot_target > 100:
        pot_target = pot_target / 1000

    with _connect() as conn:
        rows = conn.execute('SELECT * FROM catalog_inverters').fetchall()

        for row in rows:
            if _norm(row['fabricante']) == fab and _norm(row['modelo']) == mod:
                return _row_to_dict(row)
            if mod and mod in _norm(row['modelo']):
                if not fab or fab in _norm(row['fabricante']):
                    return _row_to_dict(row)

        if mod:
            for row in rows:
                row_mod = _norm(row['modelo'])
                if mod in row_mod or row_mod in mod:
                    if not fab or fab in _norm(row['fabricante']):
                        return _row_to_dict(row)

        if fab and pot_target is not None:
            best = None
            best_delta = float('inf')
            for row in rows:
                if fab not in _norm(row['fabricante']) and _norm(row['fabricante']) not in fab:
                    continue
                row_pot = _parse_potencia(row['potencia_kw'])
                if row_pot is None:
                    continue
                delta = abs(row_pot - pot_target)
                if delta < best_delta:
                    best_delta = delta
                    best = row
            if best is not None and best_delta <= 0.5:
                return _row_to_dict(best)

        if pot_target is not None and not fab:
            for row in rows:
                row_pot = _parse_potencia(row['potencia_kw'])
                if row_pot is not None and abs(row_pot - pot_target) <= 0.25:
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
        'comprimento_m': row.get('comprimento_m'),
        'largura_m': row.get('largura_m'),
        'peso_kg': row.get('peso_kg'),
    }


def catalog_inverter_to_specs(row: dict) -> dict:
    return {
        'potencia': row.get('potencia_kw'),
        'potencia_kw': row.get('potencia_kw'),
        'tipo_inversor': row.get('tipo_inversor'),
        'fase_ca': row.get('fase_ca'),
        'num_mppt': row.get('num_mppt'),
        'mppt_min': row.get('mppt_min'),
        'mppt_max': row.get('mppt_max'),
        'tensao_nominal': row.get('tensao_nominal'),
        'corrente_nominal': row.get('corrente_nominal'),
        'eficiencia': row.get('eficiencia'),
        'corrente_max_cc': row.get('corrente_max_cc'),
        'tensao_max_cc': row.get('tensao_max_cc'),
        'potencia_max_cc_kw': row.get('potencia_max_cc_kw'),
        'potencia_max_saida_ca_kw': row.get('potencia_max_saida_ca_kw'),
        'corrente_max_saida_ca': row.get('corrente_max_saida_ca'),
        'tensao_min_ca': row.get('tensao_min_ca'),
        'tensao_max_ca': row.get('tensao_max_ca'),
        'thd_pct': row.get('thd_pct'),
        'fator_potencia': row.get('fator_potencia'),
        'frequencia_hz': row.get('frequencia_hz'),
        'tensao_partida_cc': row.get('tensao_partida_cc'),
        'qtd_strings_max': row.get('qtd_strings_max'),
        'strings_por_mppt_json': row.get('strings_por_mppt_json'),
        'icc_mppt_json': row.get('icc_mppt_json'),
        'micros_max_disjuntor_ca': row.get('micros_max_disjuntor_ca'),
    }


def list_table(table: str, limit: int = 0) -> list[dict]:
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
        sql = f'SELECT * FROM {sql_table} ORDER BY id'
        if limit > 0:
            sql += f' LIMIT {limit}'
        rows = conn.execute(sql).fetchall()
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



def search_modules_fuzzy(
    query: str = '',
    fabricante: str = '',
    potencia_min: float = 0,
    potencia_max: float = 999999,
    limit: int = 10,
) -> list[dict]:
    """Busca fuzzy de módulos no catálogo."""
    potencia_min = _parse_potencia(potencia_min) or 0.0
    potencia_max = _parse_potencia(potencia_max) or 999999.0
    limit = int(_parse_potencia(limit) or 10)
    init_db()
    with _connect() as conn:
        sql = '''
            SELECT *,
                   (CASE
                       WHEN LOWER(modelo) LIKE ? THEN 3
                       WHEN LOWER(fabricante) LIKE ? THEN 2
                       ELSE 1
                   END) as relevancia
            FROM catalog_modules
            WHERE 1=1
        '''
        params = [f'%{query.lower()}%', f'%{query.lower()}%']
        
        if fabricante:
            sql += ' AND LOWER(fabricante) LIKE ?'
            params.append(f'%{fabricante.lower()}%')
        
        if potencia_min > 0:
            sql += ' AND potencia_wp >= ?'
            params.append(potencia_min)
        
        if potencia_max < 999999:
            sql += ' AND potencia_wp <= ?'
            params.append(potencia_max)
        
        sql += ' ORDER BY relevancia DESC, potencia_wp DESC LIMIT ?'
        params.append(limit)
        
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]


# Tolerância reexportada acima (MODULE_POWER_TOLERANCE_WP)


def _parse_wp_from_text(text: str) -> float:
    """Extrai potência Wp do modelo apenas para busca exata no catálogo."""
    if not text:
        return 0.0
    import re
    for pattern in (r'(\d{3,4})\s*wp\b', r'(\d{3,4})\s*w\b'):
        match = re.search(pattern, str(text), re.I)
        if match:
            try:
                return float(match.group(1))
            except (TypeError, ValueError):
                pass
    return 0.0


def find_module_by_name_or_power(fabricante: str = '', modelo: str = '', potencia_wp: float = 0) -> dict | None:
    """
    Busca módulo no catálogo — somente match confiável (sem aproximar potência).
    Retorna None se não houver entrada exata (±2 Wp no mesmo fabricante).
    """
    init_db()
    try:
        potencia_wp = float(potencia_wp or 0)
    except (TypeError, ValueError):
        potencia_wp = 0.0
    if potencia_wp <= 0 and modelo:
        potencia_wp = _parse_wp_from_text(modelo)

    if not fabricante and not modelo and potencia_wp <= 0:
        return None

    fab_norm = fabricante.lower().strip() if fabricante else ''
    mod_norm = modelo.lower().strip() if modelo else ''

    with _connect() as conn:
        # 1) fabricante + modelo exatos
        if fab_norm and mod_norm:
            row = conn.execute(
                'SELECT * FROM catalog_modules WHERE LOWER(fabricante) = ? AND LOWER(modelo) = ? LIMIT 1',
                (fab_norm, mod_norm),
            ).fetchone()
            if row:
                return _row_to_dict(row)

        # 2) fabricante + potência exata (Wp)
        if fab_norm and potencia_wp > 0:
            row = conn.execute(
                'SELECT * FROM catalog_modules WHERE LOWER(fabricante) = ? AND potencia_wp = ? LIMIT 1',
                (fab_norm, int(potencia_wp)),
            ).fetchone()
            if row:
                return _row_to_dict(row)

            # 3) mesma potência com tolerância mínima (arredondamento ±2 Wp)
            row = conn.execute(
                '''SELECT * FROM catalog_modules
                   WHERE LOWER(fabricante) = ?
                     AND ABS(potencia_wp - ?) <= ?
                   ORDER BY ABS(potencia_wp - ?) ASC LIMIT 1''',
                (fab_norm, potencia_wp, MODULE_POWER_TOLERANCE_WP, potencia_wp),
            ).fetchone()
            if row:
                return _row_to_dict(row)

    return None



def search_inverters_fuzzy(query='', fabricante='', potencia_min=0, potencia_max=999999, tipo_inversor='', limit=10):
    """
    Busca fuzzy de inversores com pontuação de relevância.
    
    Args:
        query: Termo de busca (modelo ou fabricante)
        fabricante: Filtro por fabricante
        potencia_min: Potência mínima (kW)
        potencia_max: Potência máxima (kW)
        tipo_inversor: Filtro por tipo (micro, string, central)
        limit: Máximo de resultados
    
    Returns:
        Lista de inversores ordenados por relevância
    """
    potencia_min = _parse_potencia(potencia_min) or 0.0
    potencia_max = _parse_potencia(potencia_max) or 999999.0
    limit = int(_parse_potencia(limit) or 10)
    conn = _connect()
    cursor = conn.cursor()
    
    sql = '''
        SELECT *,
               (CASE
                   WHEN LOWER(modelo) LIKE ? THEN 3
                   WHEN LOWER(fabricante) LIKE ? THEN 2
                   ELSE 1
               END) as relevancia
        FROM catalog_inverters
        WHERE 1=1
    '''
    
    params = []
    query_pattern = f'%{query.lower()}%'
    params.extend([query_pattern, query_pattern])
    
    if fabricante:
        sql += ' AND LOWER(fabricante) LIKE ?'
        params.append(f'%{fabricante.lower()}%')
    
    if potencia_min > 0:
        sql += ' AND potencia_kw >= ?'
        params.append(potencia_min)
    
    if potencia_max < 999999:
        sql += ' AND potencia_kw <= ?'
        params.append(potencia_max)
    
    if tipo_inversor:
        sql += ' AND LOWER(tipo_inversor) LIKE ?'
        params.append(f'%{tipo_inversor.lower()}%')
    
    sql += ' ORDER BY relevancia DESC, potencia_kw DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


def find_inverter_by_name_or_power(fabricante='', modelo='', potencia_kw=0):
    """
    Busca inteligente de inversor com estratégia de 3 camadas:
    1. Match exato: fabricante + modelo
    2. Match por potência exata: fabricante + potencia_kw
    3. Match com tolerância: fabricante + potencia_kw ±10%
    
    Args:
        fabricante: Nome do fabricante
        modelo: Modelo do inversor
        potencia_kw: Potência nominal (kW)
    
    Returns:
        dict com inversor encontrado ou None
    """
    try:
        potencia_kw = float(str(potencia_kw or 0).replace(',', '.'))
    except (TypeError, ValueError):
        potencia_kw = 0.0
    if potencia_kw > 100:
        potencia_kw = potencia_kw / 1000

    init_db()
    fab = _norm(fabricante)
    mod = _norm(modelo)

    with _connect() as conn:
        cursor = conn.cursor()

        # Tier 1: fabricante + modelo
        if fab and mod:
            cursor.execute(
                '''
                SELECT * FROM catalog_inverters
                WHERE LOWER(fabricante) LIKE ?
                  AND LOWER(modelo) LIKE ?
                LIMIT 1
                ''',
                (f'%{fab}%', f'%{mod}%'),
            )
            result = cursor.fetchone()
            if result:
                return _row_to_dict(result)

        # Tier 1b: só modelo (formulário sem fabricante)
        if mod:
            cursor.execute(
                '''
                SELECT * FROM catalog_inverters
                WHERE LOWER(modelo) LIKE ?
                ORDER BY ABS(COALESCE(potencia_kw, 0) - ?) ASC
                LIMIT 1
                ''',
                (f'%{mod}%', potencia_kw or 0),
            )
            result = cursor.fetchone()
            if result:
                return _row_to_dict(result)

        # Tier 2: fabricante + potência exata
        if fab and potencia_kw > 0:
            cursor.execute(
                '''
                SELECT * FROM catalog_inverters
                WHERE LOWER(fabricante) LIKE ?
                  AND potencia_kw = ?
                LIMIT 1
                ''',
                (f'%{fab}%', potencia_kw),
            )
            result = cursor.fetchone()
            if result:
                return _row_to_dict(result)

        # Tier 3: fabricante + potência ±10%
        if fab and potencia_kw > 0:
            tolerance = 0.10
            min_power = potencia_kw * (1 - tolerance)
            max_power = potencia_kw * (1 + tolerance)
            cursor.execute(
                '''
                SELECT * FROM catalog_inverters
                WHERE LOWER(fabricante) LIKE ?
                  AND potencia_kw BETWEEN ? AND ?
                ORDER BY ABS(potencia_kw - ?) ASC
                LIMIT 1
                ''',
                (f'%{fab}%', min_power, max_power, potencia_kw),
            )
            result = cursor.fetchone()
            if result:
                return _row_to_dict(result)

    return None
