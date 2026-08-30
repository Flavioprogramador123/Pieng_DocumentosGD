"""
Fatores de demanda — NTC-04 Rev.4 CELG-D / Equatorial Goiás (BT secundária).

Referência: Anexo A — Tabelas 2, 3 e 4.
Regra geral Tabela 3: 1 aparelho do mesmo tipo → FD = 100%.
"""

from __future__ import annotations

import math
from typing import Literal

EquipmentKind = Literal[
    'iluminacao',
    'tug',
    'iluminacao_tug',
    'chuveiro',
    'torneira_aquecedor_passagem',
    'lava_louca',
    'aquecedor_acumulacao',
    'secadora',
    'microondas',
    'ar_condicionado',
    'forno_fogao',
    'motor',
    'geladeira',
    'outro',
]

# Tabela 2 — Residências: FD (%) em função da potência instalada P (kW)
# iluminação + tomadas de uso geral (grupo "a" da fórmula NTC-04)
RESIDENTIAL_LIGHTING_TUG_BANDS: list[tuple[float, float, float]] = [
    (0.0, 1.0, 0.86),
    (1.0, 2.0, 0.75),
    (2.0, 3.0, 0.66),
    (3.0, 4.0, 0.59),
    (4.0, 5.0, 0.52),
    (5.0, 6.0, 0.45),
    (6.0, 7.0, 0.40),
    (7.0, 8.0, 0.35),
    (8.0, 9.0, 0.31),
    (9.0, 10.0, 0.27),
    (10.0, math.inf, 0.24),
]

# Tabela 3 — colunas por tipo (FD % indexado pela quantidade de aparelhos iguais)
# Índice 0 = 1 aparelho, 1 = 2 aparelhos, ...
_T3_CHUVEIRO = [100, 68, 56, 48, 43, 39, 36, 33, 31, 30, 30, 29, 29, 28, 28, 27, 27, 26, 26, 25, 25, 24, 23]
_T3_TORNEIRA_PASSAGEM = [100, 72, 62, 57, 54, 52, 50, 49, 48, 46, 46, 44, 44, 42, 42, 40, 40, 38, 38, 36, 36, 34, 32]
_T3_ACUMULACAO = [100, 71, 64, 60, 57, 54, 53, 51, 50, 50, 50, 50, 47, 47, 47, 46, 46, 45, 45, 45, 45, 45, 45]
_T3_SECADORA = [100, 95, 90, 85, 80, 70, 62, 50, 54, 50, 50, 46, 46, 40, 40, 36, 36, 32, 32, 26, 26, 25, 25]
_T3_MICROONDAS = [100, 60, 48, 40, 37, 35, 33, 32, 31, 30, 30, 28, 28, 26, 26, 26, 26, 26, 26, 26, 26, 24, 23]

_T3_BY_KIND: dict[str, list[int]] = {
    'chuveiro': _T3_CHUVEIRO,
    'torneira_aquecedor_passagem': _T3_TORNEIRA_PASSAGEM,
    'lava_louca': _T3_TORNEIRA_PASSAGEM,
    'aquecedor_acumulacao': _T3_ACUMULACAO,
    'secadora': _T3_SECADORA,
    'microondas': _T3_MICROONDAS,
}

# Tabela 4 — ar-condicionado residencial (quantidade de aparelhos)
_AC_RESIDENTIAL_BANDS: list[tuple[int, int, float]] = [
    (1, 10, 1.00),
    (11, 20, 0.86),
    (21, 30, 0.80),
    (31, 40, 0.78),
    (41, 50, 0.75),
    (51, 75, 0.70),
    (76, 100, 0.65),
    (101, 10_000, 0.60),
]


def _fd_from_qty_table(qty: int, table: list[int]) -> float:
    if qty <= 0:
        return 1.0
    idx = min(qty, len(table)) - 1
    return table[idx] / 100.0


def fd_residential_lighting_tug_group(p_kw: float) -> float:
    """Tabela 2 — grupo iluminação + TUG (P total em kW)."""
    p = max(float(p_kw), 0.0)
    if p <= 0:
        return 1.0
    for lo, hi, fd in RESIDENTIAL_LIGHTING_TUG_BANDS:
        if lo < p <= hi:
            return fd
    return 0.24


def fd_table3(kind: str, qty: int) -> float:
    """Tabela 3 — equipamentos de uso residencial."""
    table = _T3_BY_KIND.get(kind)
    if not table:
        return 1.0 if qty <= 1 else _fd_from_qty_table(qty, _T3_CHUVEIRO)
    return _fd_from_qty_table(max(qty, 1), table)


def fd_table4_ac_residential(qty: int) -> float:
    """Tabela 4 — ar-condicionado residencial."""
    q = max(int(qty), 1)
    for lo, hi, fd in _AC_RESIDENTIAL_BANDS:
        if lo <= q <= hi:
            return fd
    return 0.60


def fd_for_load(
    kind: str,
    qty: int,
    *,
    classe: str = 'RESIDENCIAL',
    group_p_kw: float | None = None,
) -> float:
    """
    Retorna FD (0–1) conforme NTC-04.
    kind: iluminacao | tug | chuveiro | microondas | ar_condicionado | geladeira | ...
    group_p_kw: potência acumulada (kW) do grupo iluminação+TUG, se kind in (iluminacao, tug).
    """
    k = (kind or 'outro').lower()
    q = max(int(qty), 1)
    is_res = 'RESID' in (classe or '').upper()

    if k in ('iluminacao', 'tug', 'iluminacao_tug'):
        if group_p_kw is not None and is_res:
            return fd_residential_lighting_tug_group(group_p_kw)
        return 1.0

    if k == 'ar_condicionado':
        return fd_table4_ac_residential(q) if is_res else fd_table4_ac_residential(q)  # comercial: bandas distintas

    if k in _T3_BY_KIND:
        return fd_table3(k, q)

    # Geladeira, motor pequeno e carga não tabulada: 1 unidade = 100%
    if q == 1:
        return 1.0
    # Vários motores/cargas similares — diversificação conservadora
    return max(0.70, 1.0 - 0.05 * (q - 1))


def apply_ntc04_to_loads(loads: list[dict], classe: str = 'RESIDENCIAL') -> list[dict]:
    """Calcula FD por linha e preenche ci_kw, d_kw etc."""
    enriched = []
    group_ci_kw = 0.0
    for load in loads:
        kind = (load.get('tipo') or load.get('kind') or 'outro').lower()
        if kind in ('iluminacao', 'tug', 'iluminacao_tug'):
            pot_w = float(load.get('pot_w', 0))
            qtd = float(load.get('qtd', 1))
            group_ci_kw += pot_w * qtd / 1000.0

    group_fd = (
        fd_residential_lighting_tug_group(group_ci_kw)
        if 'RESID' in classe.upper() and group_ci_kw > 0
        else 1.0
    )

    for i, load in enumerate(loads):
        pot_w = float(load['pot_w'])
        qtd = int(float(load['qtd']))
        fp = float(load.get('fp') or 0.92)
        kind = (load.get('tipo') or load.get('kind') or 'outro').lower()

        if kind in ('iluminacao', 'tug', 'iluminacao_tug'):
            fd = group_fd
            fd_ref = f'NTC-04 Tabela 2 (P grupo={group_ci_kw:.2f} kW → {int(round(group_fd * 100))}%)'
        elif kind == 'ar_condicionado':
            fd = fd_for_load(kind, qtd, classe=classe)
            fd_ref = f'NTC-04 Tabela 4 ({qtd} aparelho(s) → {int(round(fd * 100))}%)'
        elif kind in _T3_BY_KIND:
            fd = fd_for_load(kind, qtd, classe=classe)
            fd_ref = f'NTC-04 Tabela 3 ({qtd} aparelho(s) → {int(round(fd * 100))}%)'
        else:
            fd = fd_for_load(kind, qtd, classe=classe)
            fd_ref = f'NTC-04 — 1 aparelho=100%' if qtd == 1 else f'NTC-04 diversificação ({qtd} un.)'

        ci_kw = pot_w * qtd / 1000.0
        ci_kva = ci_kw / fp if fp else ci_kw
        enriched.append({
            **load,
            'item': str(i + 1),
            'pot_unit_w': int(pot_w),
            'qtd': qtd,
            'ci_kw': round(ci_kw, 2),
            'fp': fp,
            'ci_kva': round(ci_kva, 2),
            'fd': fd,
            'd_kw': round(ci_kw * fd, 2),
            'd_kva': round(ci_kva * fd, 2),
            'fd_ref': fd_ref,
        })
    return enriched
