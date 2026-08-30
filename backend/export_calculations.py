"""
Exportação de cálculos intermediários para relatórios técnicos.
Gera JSON, CSV e TXT com detalhamento completo dos cálculos.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def export_calculations_json(calc_result: dict, output_path: str | Path) -> None:
    """Exporta cálculos completos para JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(calc_result, f, ensure_ascii=False, indent=2)


def export_calculations_csv(calc_result: dict, output_path: str | Path) -> None:
    """Exporta resumo de cálculos para CSV (importável em Excel)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items = calc_result.get('all_items') or []

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')  # Excel brasileiro usa ;
        writer.writerow(['Grupo', 'Parâmetro', 'Valor', 'Token'])

        for item in items:
            writer.writerow([
                item.get('grupo', ''),
                item.get('rotulo', ''),
                item.get('valor', ''),
                item.get('token', ''),
            ])


def export_calculations_txt(calc_result: dict, output_path: str | Path) -> None:
    """Exporta relatório técnico legível em TXT."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append('='*80)
    lines.append('RELATÓRIO DE CÁLCULOS TÉCNICOS — SISTEMA FOTOVOLTAICO')
    lines.append('='*80)
    lines.append('')

    # Resumo de potência
    lines.append('1. RESUMO DE POTÊNCIA')
    lines.append('-' * 80)
    lines.append(f"Potência total módulos:     {calc_result.get('total_module_power_kw', 0):.2f} kWp")
    lines.append(f"Potência total inversores:  {calc_result.get('total_inverter_power_kw', 0):.2f} kW")
    lines.append(f"Relação DC/AC:              {calc_result.get('relacao_modulo_inversor', 0):.2f}")
    lines.append('')

    # Geração estimada
    lines.append('2. GERAÇÃO ESTIMADA')
    lines.append('-' * 80)
    lines.append(f"Geração mensal:   {calc_result.get('estimated_monthly_generation', 0):,.0f} kWh/mês".replace(',', '.'))
    lines.append(f"Geração anual:    {calc_result.get('estimated_annual_generation', 0):,.0f} kWh/ano".replace(',', '.'))
    lines.append(f"Geração diária:   {calc_result.get('estimated_daily_generation', 0):.1f} kWh/dia")
    lines.append(f"HSP utilizado:    {calc_result.get('hsp_used', 5.2):.1f} h/dia")
    lines.append(f"Eficiência:       {calc_result.get('system_efficiency_pct', 80):.0f}%")
    lines.append('')

    # Parâmetros elétricos
    lines.append('3. PARÂMETROS ELÉTRICOS')
    lines.append('-' * 80)
    voltage_info = calc_result.get('voltage_info') or {}
    lines.append(f"Tensão de atendimento:  {calc_result.get('voltage_v', 220):.0f} V")
    lines.append(f"Sistema:                {calc_result.get('system_type', 'monofasico')}")
    lines.append(f"Fórmula corrente AC:    {voltage_info.get('formula', 'P / V')}")
    lines.append(f"Corrente AC estimada:   {calc_result.get('corrente_ac_a', 0):.2f} A")
    lines.append(f"Disjuntor recomendado:  {calc_result.get('disjuntor_recomendado_a', 0)} A")
    lines.append('')

    # Strings CC
    dc_strings = calc_result.get('dc_strings') or {}
    if dc_strings:
        lines.append('4. ANÁLISE DE STRINGS CC')
        lines.append('-' * 80)
        lines.append(f"Topologia:            {dc_strings.get('topology', '—')}")
        lines.append(f"Módulos por string:   {dc_strings.get('modules_per_string', '—')}")
        lines.append(f"Total de módulos:     {dc_strings.get('total_modules', '—')}")
        lines.append(f"Total de strings:     {dc_strings.get('total_strings', '—')}")
        lines.append(f"Voc string (série):   {dc_strings.get('string_voc_v', '—')} V")
        lines.append(f"Isc string:           {dc_strings.get('string_isc_a', '—')} A")
        lines.append(f"Isc projeto (×1,25):  {dc_strings.get('isc_design_a', '—')} A")

        messages = dc_strings.get('messages') or []
        if messages:
            lines.append('')
            lines.append('Observações:')
            for msg in messages:
                lines.append(f"  • {msg}")
        lines.append('')

    # Cabos e proteções
    lines.append('5. DIMENSIONAMENTO DE CABOS E PROTEÇÕES')
    lines.append('-' * 80)
    lines.append(f"Cabo CC recomendado:  {calc_result.get('cable_section_cc', '—')}")
    lines.append(f"Cabo CA recomendado:  {calc_result.get('cable_section_ca', '—')}")

    protection = calc_result.get('protection') or {}
    if protection:
        lines.append(f"Disjuntor CA:         {protection.get('ac_breaker_a', '—')} A")
        lines.append(f"DPS recomendado:      {protection.get('dps_class', '—')} {protection.get('dps_voltage', '—')}")
    lines.append('')

    # Economia estimada
    lines.append('6. ECONOMIA ESTIMADA')
    lines.append('-' * 80)
    lines.append(f"Tarifa utilizada:      R$ {calc_result.get('tarifa_kwh', 1.10):.2f}/kWh")
    lines.append(f"Economia mensal:       R$ {calc_result.get('economia_mensal_estimada', 0):.2f}")
    lines.append(f"Economia anual:        R$ {calc_result.get('economia_mensal_estimada', 0) * 12:.2f}")
    lines.append('')

    # Tabela de demanda (se houver)
    demand_table = calc_result.get('demand_table')
    if demand_table:
        lines.append('7. LEVANTAMENTO DE CARGA (DEMANDA)')
        lines.append('-' * 80)
        memorial_text = demand_table.get('memorial_text', '')
        if memorial_text:
            lines.append(memorial_text)
        lines.append('')

    # Compatibilidade
    compatibility = calc_result.get('compatibility') or {}
    status = compatibility.get('status', 'OK')
    lines.append('8. VERIFICAÇÃO DE COMPATIBILIDADE')
    lines.append('-' * 80)
    lines.append(f"Status: {status}")

    warnings = compatibility.get('warnings') or []
    errors = compatibility.get('errors') or []

    if errors:
        lines.append('')
        lines.append('ERROS:')
        for err in errors:
            lines.append(f"  ❌ {err}")

    if warnings:
        lines.append('')
        lines.append('AVISOS:')
        for warn in warnings:
            lines.append(f"  ⚠️  {warn}")

    if not errors and not warnings:
        lines.append('  ✅ Sistema dimensionado corretamente')

    lines.append('')
    lines.append('='*80)
    lines.append('Relatório gerado automaticamente pelo Sistema Automação Equatorial')
    lines.append('='*80)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def export_all_formats(calc_result: dict, base_path: str | Path, base_name: str = 'calculos') -> dict[str, str]:
    """
    Exporta cálculos em todos os formatos disponíveis.

    Retorna dicionário com caminhos dos arquivos gerados:
    {
        'json': '/path/to/calculos.json',
        'csv': '/path/to/calculos.csv',
        'txt': '/path/to/calculos.txt'
    }
    """
    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)

    paths = {}

    json_path = base_path / f'{base_name}.json'
    export_calculations_json(calc_result, json_path)
    paths['json'] = str(json_path)

    csv_path = base_path / f'{base_name}.csv'
    export_calculations_csv(calc_result, csv_path)
    paths['csv'] = str(csv_path)

    txt_path = base_path / f'{base_name}.txt'
    export_calculations_txt(calc_result, txt_path)
    paths['txt'] = str(txt_path)

    return paths


if __name__ == '__main__':
    # Exemplo de uso
    exemplo = {
        'total_module_power_kw': 11.0,
        'total_inverter_power_kw': 10.0,
        'relacao_modulo_inversor': 1.10,
        'estimated_monthly_generation': 1584,
        'estimated_annual_generation': 19008,
        'estimated_daily_generation': 52.1,
        'hsp_used': 5.2,
        'system_efficiency_pct': 80,
        'voltage_v': 220,
        'system_type': 'monofasico',
        'corrente_ac_a': 45.45,
        'disjuntor_recomendado_a': 63,
        'cable_section_cc': '10mm²',
        'cable_section_ca': '16mm²',
        'economia_mensal_estimada': 1742.40,
        'tarifa_kwh': 1.10,
        'dc_strings': {
            'topology': 'string',
            'modules_per_string': 14,
            'total_modules': 28,
            'total_strings': 2,
            'string_voc_v': 644.0,
            'string_isc_a': 13.5,
            'isc_design_a': 16.88,
            'status': 'OK',
            'messages': ['Strings dentro da faixa MPPT do inversor']
        },
        'compatibility': {
            'status': 'OK',
            'message': 'Relação módulo/inversor dentro da faixa usual (1,10–1,30).',
            'warnings': [],
            'errors': []
        },
        'all_items': [
            {'grupo': 'Potência', 'rotulo': 'Potência total módulos', 'valor': '11.0 kWp', 'token': 'POTENCIA_TOTAL_INSTALADA'},
            {'grupo': 'Potência', 'rotulo': 'Potência total inversores', 'valor': '10.0 kW', 'token': 'POTENCIA_INVERSOR_TOTAL'},
        ]
    }

    paths = export_all_formats(exemplo, Path('../saida/calculos_exemplo'))
    print('Arquivos gerados:')
    for fmt, path in paths.items():
        print(f"  {fmt.upper()}: {path}")
