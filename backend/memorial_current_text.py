"""Textos formatados para memorial — correntes CA (micro / string)."""

from __future__ import annotations

from typing import Any


def _num(value: float, decimals: int = 2) -> str:
    if decimals <= 0:
        return str(int(round(value)))
    fmt = f'{{:.{decimals}f}}'.format(value)
    return fmt.rstrip('0').rstrip('.').replace('.', ',')


def _bitola_label(val: str) -> str:
    text = str(val or '').strip()
    if not text:
        return '6 mm²'
    if 'mm' in text.lower():
        return text
    digits = ''.join(c for c in text if c.isdigit())
    return f'{digits} mm²' if digits else text


def format_micro_qdca_memorial_currents(
    qdca: dict[str, Any],
    *,
    pot_inv_w: float,
    voltage_ln_v: float,
    network_trifasico: bool,
) -> tuple[str, str, str]:
    """
    Retorna (CALCULO_CORRENTE_SISTEMA, CALCULO_CORRENTE_INVERSOR, TENSAO_SAIDA_INVERSOR).
    Usa quebras de linha para o Word (expandidas em fill_docx).
    """
    i_micro = float(qdca.get('current_per_micro_a') or 0)
    i_worst = float(qdca.get('current_worst_phase_a') or 0)
    phases = qdca.get('phase_details') or []
    worst = max(phases, key=lambda d: d.get('current_a', 0), default=None)

    sistema_lines = [
        (
            f'I_micro = P_micro / VN = {_num(pot_inv_w, 0)} W / {_num(voltage_ln_v, 0)} V '
            f'= {_num(i_micro, 2)} A'
        ),
    ]
    if worst and worst.get('micros', 0) > 1:
        sistema_lines.append(
            f'I_fase (pior caso) = I_micro × {worst["micros"]} micros (Fase {worst["fase"]}) '
            f'= {_num(i_micro, 2)} A × {worst["micros"]} = {_num(i_worst, 2)} A'
        )
    elif worst:
        sistema_lines.append(f'Corrente na fase alimentada: {_num(i_worst, 2)} A')

    inv_lines = ['Distribuição por fase no QDCA:']
    for row in phases:
        bitola = _bitola_label(str(row.get('bitola_ca') or '6'))
        inv_lines.append(
            f'• Fase {row["fase"]}: {row["micros"]} micro-inversor(es) — '
            f'Disj. {row["breaker_a"]} A — cabo {bitola} — '
            f'I = {_num(float(row.get("current_a") or 0), 2)} A'
        )
    inv_lines.append(f'Corrente nominal por micro-inversor: {_num(i_micro, 2)} A')

    if network_trifasico:
        tensao = (
            f'{voltage_ln_v:g} V — microinversores monofásicos (Fase-Neutro), '
            f'distribuídos nas fases da rede trifásica para balanceamento de carga.'
        )
    else:
        tensao = f'{voltage_ln_v:g} V — microinversores monofásicos (Fase-Neutro).'

    return '\n'.join(sistema_lines), '\n'.join(inv_lines), tensao
