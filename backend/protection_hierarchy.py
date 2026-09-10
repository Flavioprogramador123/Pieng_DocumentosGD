"""
Tabela comparativa de proteção CA — padrão UC × usina solar.

Premissas:
- Micro: até 3 micros por disjuntor QDCA; em trifásico pode concentrar na mesma fase
  (economia de cabo) respeitando limite de potência por fase.
- String mono: inversor trifásico NÃO pode em rede monofásica; acima de 10 kW só com
  múltiplos inversores monofásicos (ex.: 12 kW = 2 × 6 kW).
- Padrão UC típico: 40 A + 10 mm² (mono monopolar / tri tripolar).
"""

from __future__ import annotations

import math
from typing import Any

from nbr5410_calculations import calculate_inverter_ac_current, standard_breaker_rating
from qdca_layout import network_type_from_ligacao, pack_micro_breaker_rows

PADRAO_DISJ_MONO_A = 40
PADRAO_DISJ_TRI_A = 40
PADRAO_BITOLA_MM2 = '10'
TRONCO_BITOLA_MM2 = '10'
RAMAL_MICRO_BITOLA_MM2 = '6'
RAMAL_STRING_BITOLA_MM2 = '6'
V_LN_DEFAULT = 220.0
V_LL_DEFAULT = 380.0
MICRO_POWER_KW_DEFAULT = 2.25
MAX_MICROS_POR_DISJUNTOR = 3
MAX_KW_POR_FASE_DEFAULT = 7.5
MAX_KW_INVERSOR_MONO = 10.0

AMPACITY_MM2_A: dict[str, int] = {
    '4': 35, '6': 45, '10': 55, '16': 70, '25': 95,
}


def _num(value: float, decimals: int = 2) -> str:
    if decimals <= 0:
        return str(int(round(value)))
    fmt = f'{{:.{decimals}f}}'.format(value)
    return fmt.rstrip('0').rstrip('.').replace('.', ',')


def _bitola_mm2(val: str | None, default: str = '6') -> str:
    text = str(val or default).strip()
    digits = ''.join(c for c in text if c.isdigit())
    return digits or default


def _bitola_label(val: str | None, default: str = '6') -> str:
    mm = _bitola_mm2(val, default)
    return f'{mm} mm²'


def _ampacity_a(bitola: str) -> int:
    return AMPACITY_MM2_A.get(_bitola_mm2(bitola), 45)


def _i_max_segment(*, disj_a: int, bitola: str) -> int:
    return min(disj_a, _ampacity_a(bitola))


def _polos_label(network_type: str) -> str:
    return 'tripolar' if network_type in ('trifasico', 'bifasico') else 'monopolar'


def _rede_label(network_type: str) -> str:
    return {
        'trifasico': 'Trifásico',
        'bifasico': 'Bifásico',
        'monofasico': 'Monofásico',
    }.get(network_type, 'Monofásico')


def _padrao_disj_a(network_type: str, user_a: int | None = None) -> int:
    if user_a and user_a > 0:
        return user_a
    return PADRAO_DISJ_TRI_A if network_type in ('trifasico', 'bifasico') else PADRAO_DISJ_MONO_A


def _parse_float_br(val) -> float | None:
    if val in (None, ''):
        return None
    try:
        return float(str(val).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def _truthy(val) -> bool:
    return str(val or '').lower().strip() in ('1', 'true', 'sim', 'yes', 'on')


def _user_corrente_proj_fase(technical: dict, fase: str, default: float) -> float:
    key = f"qdca_corrente_proj_fase_{fase.lower()}"
    parsed = _parse_float_br(technical.get(key))
    return round(parsed, 2) if parsed is not None else round(default, 2)


def _show_coupling_breaker(technical: dict, *, num_equipment: int) -> bool:
    if num_equipment <= 1:
        return False
    return _truthy(technical.get('qdca_tem_disj_acoplamento'))


def recommend_djg_a(
    *,
    network_type: str,
    worst_branch_a: int,
    i_design_worst_a: float,
    user_override: int | None = None,
) -> int:
    if user_override and user_override > 0:
        return user_override
    calc = standard_breaker_rating(i_design_worst_a)
    rating = max(calc, worst_branch_a)
    if network_type == 'trifasico':
        return 40 if rating <= 40 else standard_breaker_rating(rating)
    return max(PADRAO_DISJ_MONO_A, standard_breaker_rating(i_design_worst_a))


def resolve_string_equipment(
    power_kw_total: float,
    *,
    network_type: str,
    inverter_fase: str | None = None,
) -> list[dict[str, Any]]:
    """
    Define quantos inversores e potência unitária.
    Mono: máx. 10 kW/inversor monofásico; acima dispor em múltiplos de 6 kW quando possível.
    Tri: 1 inversor trifásico com potência total (se fase_ca trifásico).
    """
    inv_fase = (inverter_fase or 'monofasico').lower()
    if network_type == 'monofasico':
        inv_fase = 'monofasico'
        if power_kw_total > MAX_KW_INVERSOR_MONO:
            unit = 6.0
            n = max(2, math.ceil(power_kw_total / unit))
            per = round(power_kw_total / n, 2)
            return [{'power_kw': per, 'inverter_fase': 'monofasico', 'index': i + 1} for i in range(n)]
        return [{'power_kw': power_kw_total, 'inverter_fase': 'monofasico', 'index': 1}]

    if 'mono' in inv_fase:
        inv_fase = 'monofasico'
    else:
        inv_fase = 'trifasico'
    return [{'power_kw': power_kw_total, 'inverter_fase': inv_fase, 'index': 1}]


def build_protection_table(
    *,
    topology: str,
    tipo_ligacao: str | None,
    technical: dict[str, Any] | None = None,
    num_micros: int = 0,
    power_per_micro_kw: float = MICRO_POWER_KW_DEFAULT,
    power_kw_total: float = 0,
    num_inverters: int = 1,
    inverter_fase: str | None = None,
    v_ln: float = V_LN_DEFAULT,
    v_ll: float = V_LL_DEFAULT,
) -> dict[str, Any]:
    """Monta estrutura da tabela comparativa."""
    technical = technical or {}
    network = network_type_from_ligacao(tipo_ligacao)
    user_padrao = None
    de = technical.get('disjuntor_entrada')
    if de not in (None, ''):
        try:
            user_padrao = int(float(str(de).replace(',', '.')))
        except (TypeError, ValueError):
            pass
    padrao_disj = _padrao_disj_a(network, user_padrao)
    padrao_bitola = _bitola_label(technical.get('bitola_cabo_padrao') or PADRAO_BITOLA_MM2)
    tronco_bitola = _bitola_label(technical.get('qdca_bitola_tronco') or TRONCO_BITOLA_MM2)

    djg_override = None
    raw = technical.get('qdca_disjuntor_geral')
    if raw not in (None, ''):
        try:
            djg_override = int(float(str(raw).replace(',', '.')))
        except (TypeError, ValueError):
            pass

    table: dict[str, Any] = {
        'topology': topology,
        'network_type': network,
        'padrao': {
            'disjuntor_a': padrao_disj,
            'polos': _polos_label(network),
            'tipo_rede': _rede_label(network),
            'bitola': padrao_bitola,
            'i_max_a': _i_max_segment(disj_a=padrao_disj, bitola=padrao_bitola),
        },
        'usina': {
            'acoplamento': None,
            'equipamentos': [],
        },
    }

    if topology == 'micro':
        manual = None
        labels = ['A', 'B', 'C'] if network == 'trifasico' else ['A', 'B'] if network == 'bifasico' else ['A']
        raw_phases = []
        any_manual = False
        for lb in labels:
            key = f'qdca_micros_fase_{lb.lower()}'
            val = technical.get(key)
            if val not in (None, ''):
                any_manual = True
                raw_phases.append(int(float(str(val).replace(',', '.'))))
            else:
                raw_phases.append(0)
        manual = raw_phases if any_manual and sum(raw_phases) == num_micros else None
        mode = str(technical.get('qdca_distribuicao') or 'economia').lower()

        rows = pack_micro_breaker_rows(
            num_micros,
            power_per_micro_kw=power_per_micro_kw,
            network_type=network,
            manual_per_phase=manual,
            mode='balanceamento' if 'balanc' in mode else 'economia',
        )
        worst_br = max((r['breaker_a'] for r in rows), default=padrao_disj)
        i_worst = max((r['current_a'] for r in rows), default=0.0)
        i_des_worst = max((r['current_design_a'] for r in rows), default=0.0)
        djg_a = recommend_djg_a(
            network_type=network,
            worst_branch_a=worst_br,
            i_design_worst_a=i_des_worst,
            user_override=djg_override,
        )
        i_tronco = _parse_float_br(technical.get('qdca_corrente_proj_tronco')) or round(i_des_worst, 2)
        if _show_coupling_breaker(technical, num_equipment=num_micros):
            table['usina']['acoplamento'] = {
                'disjuntor_a': djg_a,
                'polos': _polos_label(network),
                'bitola': tronco_bitola,
                'i_max_a': _i_max_segment(disj_a=djg_a, bitola=tronco_bitola),
                'corrente_projeto_a': i_tronco,
                'label': 'DJG — disjuntor de acoplamento',
            }
            table['djg_a'] = djg_a
        else:
            table['usina']['acoplamento'] = None
            table['djg_a'] = None
        synced_rows: list[dict[str, Any]] = []
        for row in rows:
            br = row['breaker_a']
            bit = _bitola_label(row.get('bitola_ca'))
            ov_key = f"qdca_disj_fase_{row['fase'].lower()}"
            if technical.get(ov_key):
                try:
                    br = int(float(str(technical[ov_key]).replace(',', '.')))
                except (TypeError, ValueError):
                    pass
            bit_key = f"qdca_bitola_fase_{row['fase'].lower()}"
            if technical.get(bit_key):
                bit = _bitola_label(technical[bit_key])
            elif technical.get('bitola_cabo_ca'):
                bit = _bitola_label(technical['bitola_cabo_ca'])
            i_proj = _user_corrente_proj_fase(technical, row['fase'], row['current_a'])
            table['usina']['equipamentos'].append({
                'equipamento': row['equipamento'],
                'disjuntor_a': br,
                'polos': 'monopolar',
                'bitola': bit,
                'i_max_a': _i_max_segment(disj_a=br, bitola=bit),
                'corrente_projeto_a': i_proj,
                'corrente_nominal_a': row['current_a'],
                'fase': row['fase'],
                'micros': row['micros'],
            })
            synced = dict(row)
            synced['breaker_a'] = br
            synced['bitola_ca'] = bit
            synced_rows.append(synced)
        table['breaker_rows'] = synced_rows

    else:
        equipments = resolve_string_equipment(
            power_kw_total,
            network_type=network,
            inverter_fase=inverter_fase,
        )
        equip_rows = []
        worst_br = 0
        i_des_worst = 0.0
        for eq in equipments:
            cur = calculate_inverter_ac_current(
                eq['power_kw'],
                eq['inverter_fase'],
                v_ln,
                v_ll,
                topology='string',
            )
            br_user = technical.get('qdca_disjuntor_ca')
            br = int(cur['breaker_rated_a'])
            if br_user:
                try:
                    br = int(float(str(br_user).replace(',', '.')))
                except (TypeError, ValueError):
                    pass
            bit = _bitola_label(technical.get('qdca_bitola_ca') or RAMAL_STRING_BITOLA_MM2)
            i_nom = float(cur['current_nominal_a'])
            i_des = float(cur['current_design_a'])
            polos = str(cur.get('descricao_polos_disjuntor') or 'Monopolar').lower()
            label = (
                f"Inversor string {eq['index']} — {_num(eq['power_kw'], 1)} kW ({polos})"
                if len(equipments) > 1
                else f"Inversor string — {_num(eq['power_kw'], 1)} kW ({polos})"
            )
            i_des_user = _parse_float_br(technical.get('qdca_corrente_proj'))
            i_des_final = round(i_des_user, 2) if i_des_user is not None else round(i_nom, 2)
            equip_rows.append({
                'equipamento': label,
                'disjuntor_a': br,
                'polos': polos,
                'bitola': bit,
                'i_max_a': _i_max_segment(disj_a=br, bitola=bit),
                'corrente_projeto_a': i_des_final,
                'corrente_nominal_a': round(i_nom, 2),
            })
            worst_br = max(worst_br, br)
            i_des_worst = max(i_des_worst, i_des)

        djg_a = recommend_djg_a(
            network_type=network,
            worst_branch_a=worst_br,
            i_design_worst_a=i_des_worst,
            user_override=djg_override,
        )
        n_eq = len(equipments)
        i_tronco = _parse_float_br(technical.get('qdca_corrente_proj_tronco')) or round(i_des_worst, 2)
        if _show_coupling_breaker(technical, num_equipment=n_eq):
            table['usina']['acoplamento'] = {
                'disjuntor_a': djg_a,
                'polos': _polos_label(network),
                'bitola': tronco_bitola,
                'i_max_a': _i_max_segment(disj_a=djg_a, bitola=tronco_bitola),
                'corrente_projeto_a': i_tronco,
                'label': 'DJG — disjuntor de acoplamento',
            }
            table['djg_a'] = djg_a
        else:
            table['usina']['acoplamento'] = None
            table['djg_a'] = None
        table['usina']['equipamentos'] = equip_rows
        table['string_equipments'] = equipments

    return table


def _col(text: str, width: int) -> str:
    s = str(text)
    return s[:width].ljust(width)


def format_protection_table_text(table: dict[str, Any]) -> str:
    """Formata tabela comparativa para memorial (linhas com colunas alinhadas)."""
    p = table['padrao']
    u = table['usina']
    topo = 'MICROINVERSORES' if table.get('topology') == 'micro' else 'INVERSOR STRING'

    lines = [
        f'PROTEÇÃO CA — TABELA COMPARATIVA ({topo})',
        '',
        'RAMAL DE ENTRADA — PADRÃO UC (EXISTENTE, NÃO ALTERADO PELA USINA)',
        f"{_col('Disjuntor', 16)}| {_col('Mono/Tri', 12)}| {_col('Cabo', 10)}| I máx.",
        (
            f"{_col(f'{p['disjuntor_a']} A {p['polos']}', 16)}| "
            f"{_col(p['tipo_rede'], 12)}| "
            f"{_col(p['bitola'], 10)}| "
            f"{_num(p['i_max_a'], 0)} A"
        ),
        '',
        'USINA SOLAR — QDCA',
    ]

    ac = u.get('acoplamento')
    if ac:
        lines.extend([
            'Acoplamento / seccionamento (DJG)',
            f"{_col('Disjuntor', 16)}| {_col('Cabo', 10)}| {_col('I máx.', 8)}| I projeto",
            (
                f"{_col(f'{ac['disjuntor_a']} A {ac['polos']}', 16)}| "
                f"{_col(ac['bitola'], 10)}| "
                f"{_col(f'{_num(ac['i_max_a'], 0)} A', 8)}| "
                f"{_num(ac['corrente_projeto_a'], 2)} A"
            ),
            '',
        ])
    elif (u.get('equipamentos') or []) and len(u['equipamentos']) == 1:
        lines.append('Acoplamento: disjuntor do equipamento (sem DJG separado).')
        lines.append('')

    lines.extend([
        'Equipamentos / ramais',
        f"{_col('Equipamento', 28)}| {_col('Disjuntor', 12)}| {_col('Cabo', 8)}| "
        f"{_col('I máx.', 8)}| I projeto",
    ])
    for eq in u.get('equipamentos') or []:
        lines.append(
            f"{_col(eq['equipamento'], 28)}| "
            f"{_col(f'{eq['disjuntor_a']} A', 12)}| "
            f"{_col(eq['bitola'], 8)}| "
            f"{_col(f'{_num(eq['i_max_a'], 0)} A', 8)}| "
            f"{_num(eq['corrente_projeto_a'], 2)} A"
        )
    return '\n'.join(lines)


def protection_table_to_tokens(table: dict[str, Any]) -> dict[str, str]:
    text = format_protection_table_text(table)
    tokens = {
        'HIERARQUIA_PROTECAO_CA': text,
        'PROTECAO_CA_DESCRICAO': text,
        'TABELA_PROTECAO_CA': text,
    }
    ac = table.get('usina', {}).get('acoplamento')
    if ac:
        tokens['DISJUNTOR_GERAL_QDCA_A'] = str(ac['disjuntor_a'])
        tokens['TEXTO_DISJUNTOR_GERAL_QDCA'] = (
            f"DJG — Disj. {ac['disjuntor_a']} A {ac['polos']}"
        )
        tokens['BITOLA_TRONCO_QDCA'] = ac['bitola']
    p = table.get('padrao', {})
    tokens['DISJUNTOR_CA_PADRAO_A'] = str(p.get('disjuntor_a', PADRAO_DISJ_MONO_A))
    return tokens


# --- Integração com layout QDCA / memorial (API estável) ---

def enrich_micro_layout_protection(
    layout: dict[str, Any],
    technical: dict[str, Any] | None = None,
    *,
    tipo_ligacao: str | None = None,
    num_micros: int | None = None,
    power_per_micro_kw: float = MICRO_POWER_KW_DEFAULT,
) -> dict[str, Any]:
    technical = dict(technical or {})
    n = num_micros or sum(int(d.get('micros') or 0) for d in layout.get('phase_details') or [])
    table = build_protection_table(
        topology='micro',
        tipo_ligacao=tipo_ligacao,
        technical=technical,
        num_micros=n,
        power_per_micro_kw=power_per_micro_kw,
    )
    layout = dict(layout)
    layout['protection_table'] = table
    layout['protection_hierarchy'] = format_protection_table_text(table)
    layout['protection_text'] = layout['protection_hierarchy']
    layout['breaker_rows'] = table.get('breaker_rows', [])
    layout['djg_a'] = table.get('djg_a')
    layout['djg_poles'] = table['usina']['acoplamento']['polos'] if table['usina'].get('acoplamento') else ''
    layout['tronco_bitola'] = table['usina']['acoplamento']['bitola'] if table['usina'].get('acoplamento') else ''
    # Sincroniza phase_details com overrides do formulário (breaker_rows já aplicados)
    layout['phase_details'] = [
        {
            'fase': r['fase'],
            'micros': r['micros'],
            'current_a': r['current_a'],
            'current_design_a': r['current_design_a'],
            'breaker_a': r['breaker_a'],
            'bitola_ca': r['bitola_ca'],
        }
        for r in table.get('breaker_rows', [])
    ]
    layout['num_qdca_breakers'] = len(layout['phase_details'])
    if layout['phase_details']:
        from qdca_layout import _bitola_label

        layout['description'] = '; '.join(
            f"Fase {d['fase']}: {d['micros']} micro-inversor(es), Disj {d['breaker_a']} A, "
            f"cabo {_bitola_label(str(d.get('bitola_ca') or '6'))}"
            for d in layout['phase_details']
        )
        layout['breaker_worst_a'] = max(int(d.get('breaker_a') or 0) for d in layout['phase_details'])
    return layout


def enrich_string_layout_protection(
    layout: dict[str, Any],
    technical: dict[str, Any] | None = None,
    *,
    power_kw: float,
    tipo_ligacao: str | None = None,
    inverter_fase: str = 'monofasico',
    num_inverters: int = 1,
    v_ln: float = V_LN_DEFAULT,
    v_ll: float = V_LL_DEFAULT,
) -> dict[str, Any]:
    technical = dict(technical or {})
    table = build_protection_table(
        topology='string',
        tipo_ligacao=tipo_ligacao,
        technical=technical,
        power_kw_total=power_kw,
        num_inverters=num_inverters,
        inverter_fase=inverter_fase,
        v_ln=v_ln,
        v_ll=v_ll,
    )
    layout = dict(layout)
    layout['protection_table'] = table
    layout['protection_hierarchy'] = format_protection_table_text(table)
    layout['protection_text'] = layout['protection_hierarchy']
    eqs = table['usina']['equipamentos']
    if eqs:
        layout['disjuntor_ca_a'] = eqs[0]['disjuntor_a']
    layout['djg_a'] = table.get('djg_a')
    if table['usina'].get('acoplamento'):
        layout['djg_poles'] = table['usina']['acoplamento']['polos']
        layout['tronco_bitola'] = table['usina']['acoplamento']['bitola']
    return layout


def protection_layout_to_tokens(layout: dict[str, Any]) -> dict[str, str]:
    if layout.get('protection_table'):
        return protection_table_to_tokens(layout['protection_table'])
    tokens: dict[str, str] = {}
    if layout.get('protection_hierarchy'):
        tokens['HIERARQUIA_PROTECAO_CA'] = layout['protection_hierarchy']
        tokens['PROTECAO_CA_DESCRICAO'] = layout['protection_hierarchy']
    if layout.get('djg_a'):
        tokens['DISJUNTOR_GERAL_QDCA_A'] = str(layout['djg_a'])
        polos = layout.get('djg_poles') or 'tripolar'
        tokens['TEXTO_DISJUNTOR_GERAL_QDCA'] = f'DJG — Disj. {layout["djg_a"]} A {polos}'
    if layout.get('tronco_bitola'):
        tokens['BITOLA_TRONCO_QDCA'] = str(layout['tronco_bitola'])
    return tokens


# Aliases legados
format_micro_protection_hierarchy = format_protection_table_text
format_string_protection_hierarchy = None  # usar build_protection_table


def simulate_micro_scenarios(
    counts: list[int] | None = None,
    *,
    power_kw: float = MICRO_POWER_KW_DEFAULT,
) -> list[dict[str, str]]:
    counts = counts or [2, 3, 4]
    out = []
    for n in counts:
        for lig, rede in (('MONOFASICO', 'Mono 220 V'), ('TRIFASICO', 'Tri 220/380 V')):
            t = build_protection_table(
                topology='micro', tipo_ligacao=lig,
                num_micros=n, power_per_micro_kw=power_kw,
            )
            out.append({
                'tipo': 'micro',
                'config': f'{n} micros × {power_kw} kW',
                'rede': rede,
                'texto': format_protection_table_text(t),
            })
    return out


def simulate_string_scenarios(
    powers_kw: list[float] | None = None,
) -> list[dict[str, str]]:
    powers_kw = powers_kw or [6.0, 10.0, 12.0]
    out = []
    for kw in powers_kw:
        for lig, rede, inv_fase in (
            ('MONOFASICO', 'Mono 220 V', 'monofasico'),
            ('TRIFASICO', 'Tri 220/380 V', 'trifasico'),
        ):
            t = build_protection_table(
                topology='string',
                tipo_ligacao=lig,
                power_kw_total=kw,
                inverter_fase=inv_fase,
            )
            n_eq = len(t['usina']['equipamentos'])
            cfg = f'{kw:g} kW' + (f' ({n_eq} inv.)' if n_eq > 1 else '')
            out.append({
                'tipo': 'string',
                'config': cfg,
                'rede': rede,
                'texto': format_protection_table_text(t),
            })
    return out
