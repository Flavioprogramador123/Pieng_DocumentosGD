"""
Cálculos conforme NBR 5410 e estratégias de distribuição de carga.

REGRAS CRÍTICAS:

1. MICROINVERSORES:
   - Máximo 3 microinversores em SÉRIE por DISJUNTOR (limitação técnica)
   - Correntes CA SOMAM quando em série
   - CADA GRUPO DE ATÉ 3 MICROS = 1 DISJUNTOR CA independente
   - Em rede TRIFÁSICA: distribuir microinversores nas 3 fases (balanceamento)
   - Exemplo: 5 micros monofásico = 2 disjuntores (3 micros + 2 micros)

2. INVERSORES STRING:
   - CADA INVERSOR = 1 DISJUNTOR CA dedicado
   - TRIFÁSICO: pode conectar em rede trifásica (3 fases balanceadas)
   - MONOFÁSICO: SOMENTE pode conectar em rede monofásica
   - Bifásico: conecta em 2 fases

3. LIMITES DE POTÊNCIA POR REDE:
   - Rede MONOFÁSICA 220V: MÁXIMO 12 kW (limitação da rede)
   - Rede BIFÁSICA 220V: MÁXIMO 25 kW
   - Rede TRIFÁSICA 220V: MÁXIMO 75 kW
   - Rede TRIFÁSICA 380V (GO): MÁXIMO 75 kW
   - IMPORTANTE: Limite de 12kW em 220V monofásico é RÍGIDO

4. CÁLCULO DE CORRENTE CA (NBR 5410):
   - Monofásico (127V ou 220V): I = P / V
   - Bifásico (220V entre fases): I = P / V
   - Trifásico (220V/380V): I = P / (V × √3)
     * V = tensão linha-linha (LL)
     * Para GO: 380V trifásico

5. DISTRIBUIÇÃO DE CARGA:
   - Trifásico: dividir corrente total por 3 (balanceamento entre fases)
   - Cada fase carrega aproximadamente I_total / 3

6. QUANTIDADE DE DISJUNTORES CA:
   - Microinversores: 1 disjuntor para cada grupo de até 3 micros
   - Inversores string: 1 disjuntor por inversor
"""

from __future__ import annotations

import math
from typing import Any


def _sf(val, default=0.0) -> float:
    """Safe float conversion."""
    if val in (None, ''):
        return default
    try:
        return float(str(val).replace(',', '.'))
    except (TypeError, ValueError):
        return default


def _si(val, default=0) -> int:
    """Safe int conversion."""
    if val in (None, ''):
        return default
    try:
        return int(float(str(val).replace(',', '.')))
    except (TypeError, ValueError):
        return default


def calculate_ac_current_nbr5410(
    power_kw: float,
    voltage_v: float,
    system_type: str,
    topology: str = 'string',
    num_devices: int = 1,
    voltage_ln_v: float | None = None,
) -> dict[str, Any]:
    """
    Calcula corrente CA conforme NBR 5410.

    Args:
        power_kw: Potência total do sistema (kW)
        voltage_v: Tensão linha-linha (V) — ex: 220, 380
        system_type: 'monofasico', 'bifasico', 'trifasico'
        topology: 'micro' ou 'string'
        num_devices: Quantidade de inversores/microinversores

    Returns:
        {
            'current_total_a': corrente total do sistema (A),
            'current_per_phase_a': corrente por fase (A),
            'formula': fórmula utilizada,
            'distribution': descrição da distribuição,
            'warnings': lista de avisos,
        }
    """
    power_w = power_kw * 1000
    warnings = []
    v_ln = voltage_ln_v or voltage_v

    # MICROINVERSORES
    if topology == 'micro':
        power_per_micro_w = power_w / num_devices if num_devices > 0 else power_w

        if system_type == 'trifasico':
            micros_per_phase = math.ceil(num_devices / 3)

            if micros_per_phase > 3:
                warnings.append(
                    f'⚠️  ATENÇÃO: {micros_per_phase} microinversores por fase excede '
                    f'limite de 3 em série. Reconfigurar distribuição ou usar inversor string.'
                )

            # Micro monofásico em fase-neutro (220 V GO) — modelo memorial Equatorial
            i_micro = power_per_micro_w / v_ln if v_ln else 0
            i_total = power_w / v_ln if v_ln else 0
            i_per_phase = i_micro

            formula = f'I = P / V = {power_w:.0f}W / {v_ln:.0f}V'
            distribution = (
                f'{num_devices} microinversores monofásicos em fases distintas '
                f'(V fase-neutro = {v_ln:.0f} V). I por inversor: {i_micro:.2f} A'
            )

        elif system_type == 'monofasico':
            # Monofásico: máximo 3 microinversores em série
            if num_devices > 3:
                warnings.append(
                    f'⚠️  ATENÇÃO: {num_devices} microinversores em monofásico. '
                    f'Limite recomendado: 3 em série. Considerar inversor string.'
                )

            i_micro = power_per_micro_w / voltage_v if voltage_v else 0
            i_total = i_micro * num_devices  # Correntes somam em série
            i_per_phase = i_total

            formula = f'I = (P_micro × qtd) / V = ({power_per_micro_w:.0f}W × {num_devices}) / {voltage_v}V'
            distribution = f'{num_devices} microinversores em série (correntes somam)'

        else:  # bifasico
            # Distribuir em 2 fases
            micros_per_phase = math.ceil(num_devices / 2)

            if micros_per_phase > 3:
                warnings.append(
                    f'⚠️  {micros_per_phase} microinversores por fase excede limite de 3 em série.'
                )

            i_micro = power_per_micro_w / voltage_v if voltage_v else 0
            i_per_phase = i_micro * min(micros_per_phase, 3)
            i_total = i_per_phase * 2

            formula = f'I_micro = {power_per_micro_w:.0f}W / {voltage_v}V'
            distribution = f'{num_devices} micros em 2 fases ({micros_per_phase}/fase)'

        return {
            'current_total_a': round(i_total, 2),
            'current_per_phase_a': round(i_per_phase, 2),
            'formula': formula,
            'distribution': distribution,
            'warnings': warnings,
            'microinverters_per_phase': micros_per_phase if system_type in ('trifasico', 'bifasico') else num_devices,
        }

    # INVERSORES STRING
    else:
        if system_type == 'trifasico':
            # Inversor string trifásico: I_linha = P / (V_LL × √3)
            i_total = power_w / (voltage_v * math.sqrt(3)) if voltage_v else 0
            i_per_phase = i_total

            formula = f'I = P / (V_LL × √3) = {power_w:.0f}W / ({voltage_v:.0f}V × 1,732)'
            distribution = f'Inversor trifásico balanceado: {i_total:.2f} A (linha/fase)'

        elif system_type == 'bifasico':
            # Bifásico: I = P / V (tensão entre fases)
            i_total = power_w / voltage_v if voltage_v else 0
            i_per_phase = i_total / 2

            formula = f'I = P / V = {power_w:.0f}W / {voltage_v}V'
            distribution = f'Distribuído em 2 fases: {i_per_phase:.2f} A por fase'

        else:  # monofasico
            # Monofásico: I = P / V
            i_total = power_w / voltage_v if voltage_v else 0
            i_per_phase = i_total

            formula = f'I = P / V = {power_w:.0f}W / {voltage_v}V'
            distribution = 'Monofásico: 1 fase'

        return {
            'current_total_a': round(i_total, 2),
            'current_per_phase_a': round(i_per_phase, 2),
            'formula': formula,
            'distribution': distribution,
            'warnings': warnings,
        }


def validate_inverter_network_compatibility(
    inverter_type: str,
    network_type: str,
    topology: str = 'string',
) -> dict[str, Any]:
    """
    Valida compatibilidade entre tipo de inversor e tipo de rede.

    Args:
        inverter_type: 'monofasico', 'bifasico', 'trifasico'
        network_type: 'monofasico', 'bifasico', 'trifasico'

    Returns:
        {
            'compatible': bool,
            'status': 'OK' | 'ERRO',
            'message': str,
        }
    """
    inverter_type = (inverter_type or '').lower()
    network_type = (network_type or '').lower()

    # Microinversores monofásicos em rede trifásica/bifásica (fases distintas)
    if topology == 'micro' and 'trif' in network_type:
        return {
            'compatible': True,
            'status': 'OK',
            'message': (
                'Microinversores monofásicos distribuídos nas fases do sistema trifásico '
                '(balanceamento de carga).'
            ),
        }
    if topology == 'micro' and 'bif' in network_type:
        return {
            'compatible': True,
            'status': 'OK',
            'message': 'Microinversores monofásicos em fases distintas do sistema bifásico.',
        }

    # REGRA: Inversor monofásico SOMENTE em rede monofásica
    if 'mono' in inverter_type and 'mono' not in network_type:
        return {
            'compatible': False,
            'status': 'ERRO',
            'message': f'❌ ERRO: Inversor MONOFÁSICO não pode ser conectado em rede {network_type.upper()}. '
                       f'Use inversor trifásico ou altere a rede para monofásica.',
        }

    # REGRA: Inversor trifásico pode conectar em rede trifásica
    if 'trif' in inverter_type and 'trif' not in network_type:
        return {
            'compatible': False,
            'status': 'ERRO',
            'message': f'❌ ERRO: Inversor TRIFÁSICO requer rede trifásica. '
                       f'Rede atual: {network_type.upper()}.',
        }

    # Compatível
    return {
        'compatible': True,
        'status': 'OK',
        'message': f'✅ Inversor {inverter_type.upper()} compatível com rede {network_type.upper()}.',
    }


STANDARD_BREAKERS_A = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 150, 200, 250, 300]


def standard_breaker_rating(i_design_a: float, tolerance: float = 0.04) -> int:
    """
    Seleciona disjuntor comercial (série DIN).

    Se a corrente de projeto excede um valor comercial por margem pequena
    (até tolerance, padrão 4%), adota o comercial imediatamente inferior —
    ex.: 25,83 A → 25 A (não 26 A inexistente, nem 32 A desnecessário).
    """
    if i_design_a <= 0:
        return STANDARD_BREAKERS_A[0]

    for i, rating in enumerate(STANDARD_BREAKERS_A):
        if i_design_a <= rating:
            if i > 0:
                lower = STANDARD_BREAKERS_A[i - 1]
                if i_design_a <= lower * (1 + tolerance):
                    return lower
            return rating

    return STANDARD_BREAKERS_A[-1]


def calculate_breaker_per_phase(
    current_per_phase_a: float,
    safety_factor: float = 1.25,
) -> dict[str, Any]:
    """
    Dimensiona disjuntor por fase conforme NBR 5410.

    Args:
        current_per_phase_a: Corrente nominal por fase (A)
        safety_factor: Fator de segurança (padrão 1,25)

    Returns:
        {
            'breaker_rated_a': corrente nominal do disjuntor recomendado (A),
            'breaker_standard': valor comercial mais próximo (A),
        }
    """
    i_design = current_per_phase_a * safety_factor
    breaker_rated = standard_breaker_rating(i_design)

    return {
        'current_design_a': round(i_design, 2),
        'breaker_rated_a': breaker_rated,
        'breaker_standard': f'{breaker_rated}A',
    }


def validate_network_power_limit(
    power_kw: float,
    voltage_v: float,
    system_type: str,
) -> dict[str, Any]:
    """
    Valida se potência respeita limites da rede elétrica.

    LIMITES NBR 5410:
    - Monofásico 220V: MÁXIMO 12 kW
    - Bifásico 220V: MÁXIMO 25 kW
    - Trifásico 220V: MÁXIMO 75 kW
    - Trifásico 380V: MÁXIMO 75 kW

    Args:
        power_kw: Potência total do sistema (kW)
        voltage_v: Tensão da rede (V)
        system_type: 'monofasico', 'bifasico', 'trifasico'

    Returns:
        {
            'valid': bool,
            'status': 'OK' | 'ERRO',
            'limit_kw': limite da rede,
            'exceeded_kw': quanto excede (0 se OK),
            'message': str,
        }
    """
    system_type = system_type.lower()

    # Definir limites por tipo de rede
    if 'mono' in system_type:
        limit_kw = 12.0
        limit_name = '12 kW (rede monofásica 220V)'
    elif 'bif' in system_type:
        limit_kw = 25.0
        limit_name = '25 kW (rede bifásica 220V)'
    else:  # trifasico
        limit_kw = 75.0
        limit_name = f'75 kW (rede trifásica {int(voltage_v)}V)'

    exceeded_kw = max(0, power_kw - limit_kw)
    valid = power_kw <= limit_kw

    if valid:
        message = f'✅ OK: {power_kw:.1f} kW está dentro do limite de {limit_name}.'
        status = 'OK'
    else:
        message = (
            f'❌ ERRO: Sistema de {power_kw:.1f} kW EXCEDE o limite de {limit_name}. '
            f'Excesso: {exceeded_kw:.1f} kW. '
            f'SOLUÇÃO: Migrar para rede de maior capacidade ou reduzir potência.'
        )
        status = 'ERRO'

    return {
        'valid': valid,
        'status': status,
        'limit_kw': limit_kw,
        'limit_name': limit_name,
        'exceeded_kw': round(exceeded_kw, 2),
        'message': message,
    }


def calculate_breaker_groups_microinverters(
    num_microinverters: int,
    power_per_micro_w: float,
    voltage_v: float,
) -> dict[str, Any]:
    """
    Calcula agrupamento de microinversores por disjuntor CA.

    REGRA: Máximo 3 microinversores por disjuntor CA.

    Args:
        num_microinverters: Quantidade total de microinversores
        power_per_micro_w: Potência de cada microinversor (W)
        voltage_v: Tensão CA (V)

    Returns:
        {
            'num_breakers': quantidade de disjuntores CA necessários,
            'breaker_groups': lista de grupos [qtd_micros, corrente_A, disjuntor_A],
            'total_breakers_detail': descrição detalhada,
        }
    """
    # Dividir em grupos de até 3 microinversores
    num_breakers = math.ceil(num_microinverters / 3)

    groups = []
    remaining = num_microinverters

    for i in range(num_breakers):
        micros_in_group = min(3, remaining)
        remaining -= micros_in_group

        # Corrente do grupo (correntes somam em série)
        i_micro = power_per_micro_w / voltage_v if voltage_v else 0
        i_group = i_micro * micros_in_group

        # Disjuntor com fator de segurança 1,25 (série comercial)
        i_breaker_design = i_group * 1.25
        breaker_rated = standard_breaker_rating(i_breaker_design)

        groups.append({
            'group_id': i + 1,
            'micros_count': micros_in_group,
            'current_a': round(i_group, 2),
            'breaker_a': breaker_rated,
            'description': f'Grupo {i+1}: {micros_in_group} micro(s) em série → {i_group:.2f}A → Disjuntor {breaker_rated}A',
        })

    # Descrição geral
    if num_breakers == 1:
        detail = f'1 disjuntor CA para {num_microinverters} microinversor(es)'
    else:
        detail = f'{num_breakers} disjuntores CA: '
        detail += ' + '.join([f'{g["micros_count"]} micro(s)' for g in groups])

    return {
        'num_breakers': num_breakers,
        'breaker_groups': groups,
        'total_breakers_detail': detail,
    }


def analyze_microinverter_distribution(
    num_microinverters: int,
    network_type: str,
    power_per_micro_w: float,
    voltage_v: float,
) -> dict[str, Any]:
    """
    Analisa distribuição de microinversores em rede mono/bi/trifásica.

    Returns:
        {
            'phases': número de fases,
            'micros_per_phase': microinversores por fase,
            'series_per_phase': quantos em série por fase,
            'parallel_groups': quantos grupos em paralelo por fase,
            'current_per_micro_a': corrente de 1 microinversor,
            'current_per_phase_a': corrente total por fase,
            'num_breakers_ca': quantidade de disjuntores CA,
            'breaker_groups': grupos de microinversores por disjuntor,
            'status': 'OK' | 'ATENÇÃO' | 'ERRO',
            'warnings': [...],
        }
    """
    warnings = []

    phases = {'monofasico': 1, 'bifasico': 2, 'trifasico': 3}.get(network_type.lower(), 1)
    micros_per_phase = math.ceil(num_microinverters / phases)

    # Máximo 3 microinversores em série por fase
    if micros_per_phase > 3:
        series_per_phase = 3
        parallel_groups = math.ceil(micros_per_phase / 3)
        warnings.append(
            f'⚠️  {micros_per_phase} microinversores por fase excede limite de 3 em série. '
            f'Configuração: {series_per_phase} em série × {parallel_groups} grupos em paralelo.'
        )
        status = 'ATENÇÃO'
    else:
        series_per_phase = micros_per_phase
        parallel_groups = 1
        status = 'OK'

    i_micro = power_per_micro_w / voltage_v if voltage_v else 0

    # Correntes somam em série, multiplicam em paralelo
    i_per_phase = i_micro * series_per_phase * parallel_groups

    # Calcular quantidade de disjuntores CA
    breaker_info = calculate_breaker_groups_microinverters(
        num_microinverters, power_per_micro_w, voltage_v
    )

    return {
        'phases': phases,
        'micros_per_phase': micros_per_phase,
        'series_per_phase': series_per_phase,
        'parallel_groups': parallel_groups,
        'current_per_micro_a': round(i_micro, 2),
        'current_per_phase_a': round(i_per_phase, 2),
        'num_breakers_ca': breaker_info['num_breakers'],
        'breaker_groups': breaker_info['breaker_groups'],
        'breaker_groups_detail': breaker_info['total_breakers_detail'],
        'status': status,
        'warnings': warnings,
        'recommendation': (
            f'Distribuir {num_microinverters} microinversores em {phases} fase(s): '
            f'{series_per_phase} em série × {parallel_groups} grupo(s) em paralelo por fase. '
            f'{breaker_info["total_breakers_detail"]}.'
        ),
    }


if __name__ == '__main__':
    # Teste 1: 9 microinversores de 500W em rede trifásica 220V
    print('='*80)
    print('TESTE 1: 9 microinversores 500W em rede trifásica 220V')
    print('='*80)
    result = calculate_ac_current_nbr5410(
        power_kw=4.5,  # 9 × 500W
        voltage_v=220,
        system_type='trifasico',
        topology='micro',
        num_devices=9,
    )
    print(f"Corrente total: {result['current_total_a']} A")
    print(f"Corrente por fase: {result['current_per_phase_a']} A")
    print(f"Fórmula: {result['formula']}")
    print(f"Distribuição: {result['distribution']}")
    for warn in result['warnings']:
        print(warn)

    print('\n' + '='*80)
    print('TESTE 2: Inversor string 10kW trifásico em rede trifásica 380V (GO)')
    print('='*80)
    result = calculate_ac_current_nbr5410(
        power_kw=10,
        voltage_v=380,
        system_type='trifasico',
        topology='string',
        num_devices=1,
    )
    print(f"Corrente total: {result['current_total_a']} A")
    print(f"Corrente por fase: {result['current_per_phase_a']} A")
    print(f"Fórmula: {result['formula']}")
    print(f"Distribuição: {result['distribution']}")

    print('\n' + '='*80)
    print('TESTE 3: Compatibilidade inversor monofásico em rede trifásica')
    print('='*80)
    compat = validate_inverter_network_compatibility('monofasico', 'trifasico')
    print(compat['message'])
