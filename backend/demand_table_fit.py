"""
Ajuste de cargas para atingir demanda-alvo (kW) recalculando FD pela NTC-04.
Nunca altera FD manualmente — só potências, quantidades e composição de cargas.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from ntc04_demand_factors import apply_ntc04_to_loads

# Limites plausíveis (NTC-04 Tabela 8 / prática residencial)
CHUVEIRO_W = (3500, 7500)
AC_W = (900, 3000)
ILUM_W = (60, 200)
TUG_W = (100, 600)
MOTOR_W = (1000, 15000)


def _totals(rows: list[dict]) -> dict[str, float]:
    return {
        'd_kw': round(sum(r['d_kw'] for r in rows), 2),
        'ci_kw': round(sum(r['ci_kw'] for r in rows), 2),
    }


def _clone_loads(loads: list[dict]) -> list[dict]:
    return [copy.deepcopy(l) for l in loads]


def _scale_pot_w(loads: list[dict], factor: float, tipos: set[str] | None = None) -> list[dict]:
    out = []
    for load in loads:
        item = copy.deepcopy(load)
        tipo = (item.get('tipo') or 'outro').lower()
        if tipos is None or tipo in tipos:
            item['pot_w'] = max(40, int(round(float(item['pot_w']) * factor)))
        out.append(item)
    return out


def _demand(loads: list[dict], classe: str) -> tuple[float, list[dict]]:
    rows = apply_ntc04_to_loads(loads, classe)
    return _totals(rows)['d_kw'], rows


def _binary_search_scale(
    loads: list[dict],
    target_kw: float,
    classe: str,
    *,
    tipos: set[str] | None = None,
    lo: float = 0.15,
    hi: float = 4.0,
    tol: float = 0.2,
    max_iter: int = 80,
) -> tuple[list[dict], float, float]:
    """Retorna (rows, d_kw, erro)."""
    best_rows: list[dict] | None = None
    best_err = math.inf
    best_d = 0.0

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        scaled = _scale_pot_w(loads, mid, tipos)
        d_kw, rows = _demand(scaled, classe)
        err = abs(d_kw - target_kw)
        if err < best_err:
            best_err = err
            best_rows = rows
            best_d = d_kw
        if err <= tol:
            return rows, d_kw, err
        if d_kw < target_kw:
            lo = mid
        else:
            hi = mid

    assert best_rows is not None
    return best_rows, best_d, best_err


def _residential_candidates(target_kw: float) -> list[list[dict]]:
    """Perfis de carga residencial por faixa de demanda-alvo."""
    from demand_table import RESIDENTIAL_LOADS

    profiles: list[list[dict]] = []

    chuveiro_opts = [3500, 4400, 5500, 6500, 7500]
    chuveiro_qtd = [1, 1, 1, 2] if target_kw >= 12 else [1]
    ac_qtd_opts = [0, 1, 1, 2, 2, 3]
    ac_w_opts = [900, 1200, 1800, 2400]
    ilum_qtd = [6, 8, 10, 12, 14, 16]
    tug_qtd = [4, 6, 8, 10, 12]

    for cw in chuveiro_opts:
        for cq in chuveiro_qtd:
            for aq in ac_qtd_opts:
                for aw in ac_w_opts:
                    if aq == 0 and aw != 900:
                        continue
                    for iq in ilum_qtd:
                        for tq in tug_qtd:
                            loads = _clone_loads(RESIDENTIAL_LOADS)
                            loads[0]['qtd'] = iq
                            loads[1]['qtd'] = tq
                            loads[2]['pot_w'] = cw
                            loads[2]['qtd'] = cq
                            loads[5]['qtd'] = aq
                            if aq > 0:
                                loads[5]['pot_w'] = aw
                            else:
                                loads = [l for l in loads if l.get('tipo') != 'ar_condicionado']
                            if target_kw >= 14 and not any(l.get('tipo') == 'secadora' for l in loads):
                                loads.append({
                                    'descricao': 'Secadora de roupas',
                                    'tipo': 'secadora',
                                    'pot_w': 2000,
                                    'qtd': 1,
                                    'fp': 0.85,
                                })
                            profiles.append(loads)

    # Limitar combinações — amostragem por faixa alvo
    if len(profiles) > 400:
        step = max(1, len(profiles) // 400)
        profiles = profiles[::step]

    return profiles


def _industrial_candidates(target_kw: float) -> list[list[dict]]:
    from demand_table import REFERENCE_LOADS

    profiles = [_clone_loads(REFERENCE_LOADS)]
    for scale in (0.5, 0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 1.8, 2.0, 2.5):
        loads = _scale_pot_w(REFERENCE_LOADS, scale)
        profiles.append(loads)
    if target_kw >= 25:
        extra = _clone_loads(REFERENCE_LOADS)
        extra.append({
            'descricao': 'Motor adicional / linha produção',
            'tipo': 'motor',
            'pot_w': 7500,
            'qtd': 1,
            'fp': 0.85,
        })
        profiles.append(extra)
    return profiles


def _pick_best_profile(candidates: list[list[dict]], target_kw: float, classe: str) -> tuple[list[dict], list[dict], float]:
    best_loads = candidates[0]
    best_rows: list[dict] = []
    best_err = math.inf
    best_d = 0.0

    for loads in candidates:
        d_kw, rows = _demand(loads, classe)
        err = abs(d_kw - target_kw)
        if err < best_err:
            best_err = err
            best_rows = rows
            best_d = d_kw
            best_loads = loads

    return best_loads, best_rows, best_d


def fit_loads_to_target(
    loads: list[dict],
    target_kw: float,
    classe: str,
    *,
    tolerance: float = 0.25,
) -> tuple[list[dict], float, str]:
    """
    Ajusta cargas para aproximar demanda-alvo com FD sempre pela NTC-04.
    Retorna (rows, d_kw_calculado, nota_ajuste).
    """
    target_kw = float(target_kw)
    is_res = 'RESID' in (classe or '').upper()

    # 1) Busca em perfis pré-definidos
    if is_res:
        candidates = _residential_candidates(target_kw)
    else:
        candidates = _industrial_candidates(target_kw)
    candidates.append(_clone_loads(loads))

    base_loads, _, _ = _pick_best_profile(candidates, target_kw, classe)

    # 2) Refino contínuo — escala cargas principais (FD recalculado a cada passo)
    scalable = {'chuveiro', 'ar_condicionado', 'motor', 'secadora', 'microondas', 'geladeira'}
    rows, d_kw, err = _binary_search_scale(
        base_loads, target_kw, classe, tipos=scalable, tol=tolerance,
    )

    # 3) Se ainda longe, escala também iluminação/TUG (muda faixa Tabela 2)
    if err > tolerance:
        rows, d_kw, err = _binary_search_scale(
            base_loads, target_kw, classe, tipos=None, tol=tolerance,
        )

    note = (
        f'Cargas dimensionadas para demanda-alvo {target_kw:.2f} kW '
        f'(calculada {d_kw:.2f} kW, FD NTC-04).'
    )
    if err > tolerance:
        note += f' Diferença residual {err:.2f} kW — revisar potências in loco.'

    return rows, d_kw, note


def build_fitted_table_rows(
    base_loads: list[dict] | None,
    target_kw: float,
    classe: str,
) -> tuple[list[dict], float, str]:
    """Ponto de entrada: partida de template ou IA → tabela ajustada ao alvo."""
    from demand_table import REFERENCE_LOADS, RESIDENTIAL_LOADS

    if not base_loads:
        base_loads = RESIDENTIAL_LOADS if 'RESID' in classe.upper() else REFERENCE_LOADS

    return fit_loads_to_target(_clone_loads(base_loads), target_kw, classe)
