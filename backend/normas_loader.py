"""
Carrega normas técnicas Equatorial Goiás (JSON) para padrão de entrada,
tabelas de cabos, tensões e demanda fornecida.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

NORMAS_PATH = Path(__file__).resolve().parent.parent / 'dados' / 'normas_equatorial_go.json'


def _norm_ligacao(value: str | None) -> str:
    t = (value or 'MONOFASICO').upper()
    if 'TRIF' in t:
        return 'TRIFASICO'
    if 'BIF' in t:
        return 'BIFASICO'
    return 'MONOFASICO'


def _norm_classe(value: str | None) -> str:
    base = (value or 'RESIDENCIAL').upper()
    if 'COM' in base:
        return 'COMERCIAL'
    if 'IND' in base:
        return 'INDUSTRIAL'
    return 'RESIDENCIAL'


def _norm_uf(value: str | None) -> str:
    return (value or 'GO').upper()[:2]


@lru_cache(maxsize=1)
def load_normas() -> dict[str, Any]:
    if not NORMAS_PATH.is_file():
        return {}
    return json.loads(NORMAS_PATH.read_text(encoding='utf-8'))


def get_uf_voltage_map() -> dict[str, dict[str, float]]:
    """Mapa UF → {monofasico, bifasico, trifasico} em V para grid_voltage."""
    normas = load_normas()
    result: dict[str, dict[str, float]] = {}
    for uf, tipos in (normas.get('tensoes') or {}).items():
        entry: dict[str, float] = {}
        for tipo, spec in tipos.items():
            if isinstance(spec, dict):
                if 'v_ll_v' in spec:
                    entry['trifasico'] = float(spec['v_ll_v'])
                if 'vn_v' in spec:
                    if tipo == 'trifasico' and 'trifasico' not in entry:
                        entry['trifasico'] = float(spec.get('v_ll_v') or spec['vn_v'])
                    entry.setdefault('monofasico', float(spec['vn_v']))
                    entry.setdefault('bifasico', float(spec['vn_v']))
        if entry:
            result[uf] = entry
    return result


def get_padrao_entrada(
    uf: str | None = None,
    tipo_ligacao: str | None = None,
    classe: str | None = None,
) -> dict[str, Any] | None:
    """Retorna padrão de entrada GO mais específico disponível."""
    normas = load_normas()
    rows = normas.get('padrao_entrada') or []
    if not rows:
        return None

    uf_k = _norm_uf(uf)
    lig = _norm_ligacao(tipo_ligacao)
    cls = _norm_classe(classe)

    def score(row: dict) -> tuple[int, int]:
        s = 0
        if _norm_uf(row.get('uf')) == uf_k:
            s += 4
        elif row.get('uf') == 'DEFAULT':
            s += 1
        if _norm_ligacao(row.get('tipo_ligacao')) == lig:
            s += 2
        if _norm_classe(row.get('classe')) == cls:
            s += 1
        return (s, 0)

    best = max(rows, key=score)
    if score(best)[0] < 3 and uf_k != 'DEFAULT':
        fallback = get_padrao_entrada('DEFAULT', lig, cls)
        if fallback and score(fallback)[0] >= score(best)[0]:
            return fallback
    return dict(best) if score(best)[0] >= 3 else dict(best)


def _pick_from_table(
    table: list[dict],
    *,
    potencia: float | None = None,
    corrente: float | None = None,
    disjuntor: float | None = None,
    potencia_key: str = 'potencia_kwp_max',
    corrente_key: str = 'isc_a_max',
    disjuntor_key: str = 'disjuntor_a_max',
) -> str | None:
    for row in table:
        if disjuntor is not None and row.get(disjuntor_key) is not None:
            if disjuntor <= float(row[disjuntor_key]):
                return row.get('bitola_mm2')
        if potencia is not None and row.get(potencia_key) is not None:
            if potencia <= float(row[potencia_key]):
                return row.get('bitola_mm2')
        if corrente is not None and row.get(corrente_key) is not None:
            if corrente <= float(row[corrente_key]):
                return row.get('bitola_mm2')
    return table[-1].get('bitola_mm2') if table else None


def get_bitola_cc(potencia_kwp: float, isc_a: float | None = None) -> str:
    normas = load_normas()
    table = (normas.get('tabela_cabos') or {}).get('cc_modulo_inversor') or []
    if isc_a is not None:
        bitola = _pick_from_table(table, corrente=isc_a, corrente_key='isc_a_max')
        if bitola:
            return bitola
    return _pick_from_table(table, potencia=potencia_kwp, potencia_key='potencia_kwp_max') or '4 mm²'


def get_bitola_ca(potencia_kw: float, corrente_a: float | None = None) -> str:
    normas = load_normas()
    table = (normas.get('tabela_cabos') or {}).get('ca_inversor_padrao') or []
    if corrente_a is not None:
        bitola = _pick_from_table(table, corrente=corrente_a, corrente_key='corrente_a_max')
        if bitola:
            return bitola
    return _pick_from_table(table, potencia=potencia_kw, potencia_key='potencia_kw_max') or '6 mm²'


def get_bitola_padrao(disjuntor_a: float | int) -> str:
    normas = load_normas()
    table = (normas.get('tabela_cabos') or {}).get('ca_padrao_entrada') or []
    return _pick_from_table(table, disjuntor= float(disjuntor_a)) or '10 mm²'


def calc_pd_max_kw(
    uf: str | None,
    tipo_ligacao: str | None,
    disjuntor_a: float | int,
    fp: float | None = None,
) -> float | None:
    """Demanda fornecida máxima (kW) conforme tabela ou fórmula."""
    normas = load_normas()
    uf_k = _norm_uf(uf)
    lig = _norm_ligacao(tipo_ligacao)
    idg = float(disjuntor_a)

    for row in (normas.get('demanda_fornecida') or {}).get('pd_por_disjuntor') or []:
        if (
            _norm_uf(row.get('uf')) == uf_k
            and _norm_ligacao(row.get('tipo_ligacao')) == lig
            and float(row.get('disjuntor_a', 0)) == idg
        ):
            return float(row['pd_kw'])

    fp_val = fp or float((normas.get('demanda_fornecida') or {}).get('fator_potencia_padrao') or 0.92)
    nf_map = (normas.get('demanda_fornecida') or {}).get('nf_por_tipo_ligacao') or {}
    nf = int(nf_map.get(lig, 1))
    padrao = get_padrao_entrada(uf_k, lig)
    vn = 220.0
    if padrao:
        nums = [float(n) for n in re.findall(r'\d+', str(padrao.get('tensao_v', '220')))]
        if nums:
            vn = nums[0]
    return round(vn * idg * nf * fp_val / 1000, 3)


def suggest_demanda_alvo_kw(
    potencia_instalada_kw: float | None = None,
    uf: str | None = None,
    tipo_ligacao: str | None = None,
    disjuntor_a: float | int | None = None,
    classe: str | None = None,
) -> float | None:
    """
    Sugere demanda-alvo plausível para tabela NTC-04.
    Usa min(PD máx, potência instalada arredondada) ou valores típicos residenciais.
    """
    normas = load_normas()
    tipicos = (normas.get('demanda_fornecida') or {}).get('demanda_alvo_residencial_kw') or [6, 8]

    pd_max = None
    if disjuntor_a:
        pd_max = calc_pd_max_kw(uf, tipo_ligacao, disjuntor_a)

    if potencia_instalada_kw and potencia_instalada_kw > 0:
        alvo = round(min(potencia_instalada_kw, pd_max or potencia_instalada_kw), 1)
        if alvo >= 3:
            return alvo

    if pd_max:
        for kw in reversed(tipicos):
            if kw <= pd_max:
                return float(kw)
        return round(pd_max * 0.85, 1)

    return float(tipicos[min(1, len(tipicos) - 1)]) if tipicos else 6.0


def get_hsp(uf: str | None = None) -> float:
    normas = load_normas()
    uf_k = _norm_uf(uf)
    hsp_block = (normas.get('hsp') or {}).get(uf_k) or (normas.get('hsp') or {}).get('GO') or {}
    return float(hsp_block.get('media_h_dia') or 5.2)


def iter_padrao_seed_rows() -> list[tuple]:
    """Linhas para catalog_padrao: uf, tipo_ligacao, tensao_v, disjuntor_a, bitola, dps, curva, dr, notas."""
    rows = []
    seen = set()
    for item in load_normas().get('padrao_entrada') or []:
        key = (item.get('uf'), item.get('tipo_ligacao'))
        if key in seen:
            continue
        seen.add(key)
        rows.append((
            item.get('uf'),
            item.get('tipo_ligacao'),
            item.get('tensao_v'),
            int(item.get('disjuntor_a') or 40),
            item.get('bitola_cabo_padrao_mm2') or '10 mm²',
            item.get('dps_tipo') or 'DPS Classe II',
            item.get('curva_disjuntor') or 'C',
            int(item.get('dr_ma') or 30),
            item.get('notas') or '',
        ))
    return rows


def build_ai_context(mode: str = 'completo') -> str:
    """Texto compacto das normas para prompts de IA."""
    normas = load_normas()
    if not normas:
        return ''

    meta = normas.get('meta') or {}
    parts = [
        f"Normas: {meta.get('concessionaria', 'Equatorial GO')} — {', '.join(meta.get('referencias', [])[:2])}",
    ]

    padrao = get_padrao_entrada('GO', 'MONOFASICO', 'RESIDENCIAL')
    if padrao:
        parts.append(
            f"Padrão GO residencial mono: {padrao.get('tensao_v')}, disjuntor {padrao.get('disjuntor_a')} A, "
            f"cabos CC/CA/padrão {padrao.get('bitola_cabo_cc_mm2')}/{padrao.get('bitola_cabo_ca_inversor_mm2')}/"
            f"{padrao.get('bitola_cabo_padrao_mm2')}, DPS {padrao.get('dps_tipo')}, curva {padrao.get('curva_disjuntor')}"
        )

    pd_mono = calc_pd_max_kw('GO', 'MONOFASICO', 40)
    if pd_mono:
        parts.append(f"PD máxima mono 40 A GO ≈ {pd_mono} kW (FP 0,92)")

    ia = normas.get('ia_instrucoes') or {}
    if mode in ('extracao', 'completo'):
        parts.append('Extração TXT: ' + '; '.join(ia.get('extracao_txt') or [])[:4])
    if mode in ('demanda', 'completo'):
        parts.append('Demanda: ' + '; '.join(ia.get('demanda_levantamento') or [])[:3])

    tokens = normas.get('tokens_guia') or {}
    if mode == 'completo' and tokens:
        parts.append('Tokens: ' + ', '.join(list(tokens.keys())[:8]))

    return '\n'.join(parts)


def apply_normas_to_payload(normalized: dict[str, Any]) -> None:
    """Preenche lacunas no payload normalizado conforme normas GO (in-place)."""
    cliente = normalized.setdefault('cliente', {})
    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})

    uf = _norm_uf(cliente.get('uf'))
    lig = _norm_ligacao(uc.get('tipo_ligacao'))
    cls = _norm_classe(uc.get('classe'))
    padrao = get_padrao_entrada(uf, lig, cls)
    if not padrao:
        return

    def _empty(val: Any) -> bool:
        return val is None or str(val).strip() == ''

    if _empty(uc.get('tensao_atendimento')):
        uc['tensao_atendimento'] = padrao.get('tensao_v')
    if _empty(uc.get('disjuntor_entrada')):
        uc['disjuntor_entrada'] = str(padrao.get('disjuntor_a'))
    if _empty(tec.get('bitola_cabo_padrao')):
        tec['bitola_cabo_padrao'] = padrao.get('bitola_cabo_padrao_mm2')
    if _empty(tec.get('bitola_cabo_ca')):
        tec['bitola_cabo_ca'] = padrao.get('bitola_cabo_ca_inversor_mm2')
    if _empty(tec.get('bitola_cabo_cc')):
        tec['bitola_cabo_cc'] = padrao.get('bitola_cabo_cc_mm2')
    if _empty(tec.get('dps_tipo')):
        tec['dps_tipo'] = padrao.get('dps_tipo')
        tec.setdefault('dps_cc', padrao.get('dps_tipo'))
    if _empty(tec.get('dps_classe')):
        tec['dps_classe'] = padrao.get('dps_classe_v')
    if _empty(tec.get('disjuntor_curva')):
        tec['disjuntor_curva'] = padrao.get('curva_disjuntor')
    if _empty(tec.get('dr_sensibilidade_ma')):
        tec['dr_sensibilidade_ma'] = str(padrao.get('dr_ma'))

    # Potência instalada → bitolas dinâmicas
    pot_mod = 0.0
    for mod in normalized.get('modulos') or []:
        try:
            q = float(mod.get('quantidade') or mod.get('quantity') or 0)
            p = float(str(mod.get('potencia') or mod.get('power') or 0).replace(',', '.'))
            pot_mod += q * p / 1000
        except (TypeError, ValueError):
            pass

    pot_inv = 0.0
    for inv in normalized.get('inversores') or []:
        try:
            q = float(inv.get('quantidade') or inv.get('quantity') or 0)
            p = float(str(inv.get('potencia') or inv.get('power') or 0).replace(',', '.'))
            pot_inv += q * p
        except (TypeError, ValueError):
            pass

    # Bitolas dinâmicas — só sugerir quando o usuário não informou (nunca sobrescrever escolha manual)
    if pot_mod > 0 and _empty(tec.get('bitola_cabo_cc')):
        tec['bitola_cabo_cc'] = get_bitola_cc(pot_mod)
    if pot_inv > 0 and _empty(tec.get('bitola_cabo_ca')):
        tec['bitola_cabo_ca'] = get_bitola_ca(pot_inv)

    try:
        idg = float(str(uc.get('disjuntor_entrada') or padrao.get('disjuntor_a')).replace(',', '.'))
        if _empty(tec.get('bitola_cabo_padrao')):
            tec['bitola_cabo_padrao'] = get_bitola_padrao(idg)
    except (TypeError, ValueError):
        pass

    # Demanda-alvo sugerida se ausente
    if _empty(tec.get('demanda_alvo_kw')):
        alvo = suggest_demanda_alvo_kw(
            potencia_instalada_kw=max(pot_mod, pot_inv) or None,
            uf=uf,
            tipo_ligacao=lig,
            disjuntor_a=uc.get('disjuntor_entrada') or padrao.get('disjuntor_a'),
            classe=cls,
        )
        if alvo:
            tec['demanda_alvo_kw'] = str(alvo).replace('.', ',')

    tec.setdefault('normas_uf', uf)
    tec.setdefault('normas_fonte', 'normas_equatorial_go.json')
