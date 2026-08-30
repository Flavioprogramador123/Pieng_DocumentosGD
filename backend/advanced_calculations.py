import math

def _to_number(value, as_int=False):
    if value in (None, ''):
        return 0
    try:
        number = float(str(value).replace(',', '.'))
        return int(number) if as_int else number
    except (TypeError, ValueError):
        return 0

def calculate_cable_section_advanced(power_w, voltage_v=220, distance_m=50, temperature_factor=0.8, grouping_factor=0.8):
    """
    Cálculo avançado de seção de cabo baseado na NR5410
    
    Args:
        power_w: Potência em Watts
        voltage_v: Tensão em Volts
        distance_m: Distância do cabo em metros
        temperature_factor: Fator de temperatura (0.8 para 40°C)
        grouping_factor: Fator de agrupamento (0.8 para múltiplos cabos)
    
    Returns:
        dict: Seção recomendada e cálculos detalhados
    """
    
    # Corrente nominal
    current_a = power_w / voltage_v
    
    # Corrente corrigida pelos fatores
    corrected_current = current_a / (temperature_factor * grouping_factor)
    
    # Queda de tensão máxima permitida (3% para circuitos terminais)
    max_voltage_drop = voltage_v * 0.03
    
    # Resistividade do cobre (ohm.mm²/m)
    copper_resistivity = 0.0175
    
    # Cálculo da seção mínima por queda de tensão
    # V = 2 * ρ * L * I / S (para circuito monofásico)
    min_section_voltage_drop = (2 * copper_resistivity * distance_m * current_a) / max_voltage_drop
    
    # Seções padronizadas (mm²)
    standard_sections = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240]
    
    # Capacidade de corrente por seção (A) - método B1 (eletroduto embutido em alvenaria)
    current_capacity = {
        1.5: 15.5, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 68, 25: 89,
        35: 110, 50: 134, 70: 171, 95: 207, 120: 239, 150: 272,
        185: 310, 240: 364
    }
    
    # Encontrar seção adequada por capacidade de corrente
    section_by_current = None
    for section in standard_sections:
        if current_capacity.get(section, 0) >= corrected_current:
            section_by_current = section
            break
    
    # Encontrar seção adequada por queda de tensão
    section_by_voltage_drop = None
    for section in standard_sections:
        if section >= min_section_voltage_drop:
            section_by_voltage_drop = section
            break
    
    # A seção final é a maior entre as duas
    final_section = max(section_by_current or 240, section_by_voltage_drop or 240)
    
    return {
        'nominal_current_a': round(current_a, 2),
        'corrected_current_a': round(corrected_current, 2),
        'min_section_voltage_drop_mm2': round(min_section_voltage_drop, 2),
        'section_by_current_mm2': section_by_current,
        'section_by_voltage_drop_mm2': section_by_voltage_drop,
        'recommended_section_mm2': final_section,
        'voltage_drop_v': round((2 * copper_resistivity * distance_m * current_a) / final_section, 2),
        'voltage_drop_percent': round(((2 * copper_resistivity * distance_m * current_a) / final_section) / voltage_v * 100, 2)
    }

def calculate_protection_devices_advanced(power_w, voltage_v=220, system_type='monofasico'):
    """
    Cálculo avançado de dispositivos de proteção
    
    Args:
        power_w: Potência em Watts
        voltage_v: Tensão em Volts
        system_type: Tipo do sistema (monofasico, bifasico, trifasico)
    
    Returns:
        dict: Dispositivos de proteção recomendados
    """
    
    # Corrente nominal
    if system_type == 'trifasico':
        current_a = power_w / (voltage_v * math.sqrt(3))
    else:
        current_a = power_w / voltage_v
    
    from nbr5410_calculations import standard_breaker_rating

    # Disjuntor DC/CA — 125% da corrente nominal, série comercial (10, 16, 20, 25, 32…)
    dc_breaker_rating = standard_breaker_rating(current_a * 1.25)
    ac_breaker_rating = standard_breaker_rating(current_a * 1.25)
    
    # Fusível de string (se aplicável) - 150% da corrente de curto-circuito do módulo
    # Assumindo Isc = 10A para módulos típicos
    string_fuse_rating = 15  # 150% de 10A
    
    # DPS (Dispositivo de Proteção contra Surtos)
    if voltage_v <= 230:
        dps_class = "Classe II"
        dps_voltage = "275V"
    elif voltage_v <= 400:
        dps_class = "Classe II"
        dps_voltage = "440V"
    else:
        dps_class = "Classe I"
        dps_voltage = "12.5kV"
    
    # DR (Dispositivo Residual) - obrigatório para sistemas até 1MW
    dr_rating = max(30, math.ceil(current_a * 1.3))  # Mínimo 30mA
    dr_sensitivity = 30 if power_w <= 100000 else 300  # 30mA até 100kW, 300mA acima
    
    return {
        'nominal_current_a': round(current_a, 2),
        'dc_breaker_a': dc_breaker_rating,
        'ac_breaker_a': ac_breaker_rating,
        'string_fuse_a': string_fuse_rating,
        'dps_class': dps_class,
        'dps_voltage': dps_voltage,
        'dr_rating_a': dr_rating,
        'dr_sensitivity_ma': dr_sensitivity,
        'system_type': system_type
    }

def calculate_energy_generation(modules_data, location_data=None):
    """
    Cálculo de geração de energia baseado em dados reais
    
    Args:
        modules_data: Lista de dicionários com dados dos módulos
        location_data: Dados de localização (irradiação solar)
    
    Returns:
        dict: Estimativas de geração
    """
    
    # Dados padrão para o Maranhão (São Luís)
    if location_data is None:
        location_data = {
            'daily_irradiation_kwh_m2': 5.2,  # kWh/m²/dia
            'performance_ratio': 0.85,  # Fator de performance típico
            'degradation_rate': 0.005  # 0.5% ao ano
        }
    
    total_power_wp = 0
    total_area_m2 = 0
    
    for module in modules_data:
        quantity = _to_number(module.get('quantity', module.get('quantidade', 0)), as_int=True)
        power_wp = _to_number(module.get('power', module.get('potencia', 0)))
        if quantity <= 0 or power_wp <= 0:
            continue

        # Área típica de módulo (assumindo 2m²/módulo para 400W)
        module_area = power_wp / 200  # m²

        total_power_wp += quantity * power_wp
        total_area_m2 += quantity * module_area
    
    # Geração diária (kWh/dia)
    daily_generation = (total_power_wp / 1000) * location_data['daily_irradiation_kwh_m2'] * location_data['performance_ratio']
    
    # Geração mensal (kWh/mês)
    monthly_generation = daily_generation * 30
    
    # Geração anual (kWh/ano)
    annual_generation = daily_generation * 365
    
    # Geração ao longo de 25 anos considerando degradação
    generation_25_years = []
    for year in range(1, 26):
        yearly_generation = annual_generation * ((1 - location_data['degradation_rate']) ** (year - 1))
        generation_25_years.append(round(yearly_generation, 2))
    
    total_25_years = sum(generation_25_years)
    
    return {
        'total_power_kw': round(total_power_wp / 1000, 2),
        'total_area_m2': round(total_area_m2, 2),
        'daily_generation_kwh': round(daily_generation, 2),
        'monthly_generation_kwh': round(monthly_generation, 2),
        'annual_generation_kwh': round(annual_generation, 2),
        'generation_25_years_kwh': generation_25_years,
        'total_25_years_kwh': round(total_25_years, 2),
        'performance_ratio': location_data['performance_ratio'],
        'irradiation_kwh_m2_day': location_data['daily_irradiation_kwh_m2']
    }

def calculate_economic_analysis(system_cost, monthly_generation_kwh, electricity_tariff=0.85, inflation_rate=0.04, discount_rate=0.10):
    """
    Análise econômica do sistema fotovoltaico
    
    Args:
        system_cost: Custo total do sistema (R$)
        monthly_generation_kwh: Geração mensal (kWh)
        electricity_tariff: Tarifa de energia (R$/kWh)
        inflation_rate: Taxa de inflação anual
        discount_rate: Taxa de desconto anual
    
    Returns:
        dict: Análise econômica completa
    """
    
    # Economia mensal inicial
    monthly_savings = monthly_generation_kwh * electricity_tariff
    annual_savings = monthly_savings * 12
    
    # Payback simples
    simple_payback_years = system_cost / annual_savings
    
    # Fluxo de caixa para 25 anos
    cash_flow = [-system_cost]  # Investimento inicial
    
    for year in range(1, 26):
        # Economia anual com inflação da tarifa
        yearly_savings = annual_savings * ((1 + inflation_rate) ** year)
        cash_flow.append(yearly_savings)
    
    # VPL (Valor Presente Líquido)
    npv = 0
    for i, cf in enumerate(cash_flow):
        npv += cf / ((1 + discount_rate) ** i)
    
    # TIR (Taxa Interna de Retorno) - aproximação
    # Usando método iterativo simples
    tir = None
    for rate in [r/1000 for r in range(1, 500)]:  # 0.1% a 50%
        test_npv = sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flow))
        if abs(test_npv) < 100:  # Próximo de zero
            tir = rate
            break
    
    # Payback descontado
    discounted_payback_years = None
    cumulative_pv = 0
    for year in range(1, 26):
        yearly_pv = cash_flow[year] / ((1 + discount_rate) ** year)
        cumulative_pv += yearly_pv
        if cumulative_pv >= system_cost:
            discounted_payback_years = year
            break
    
    return {
        'system_cost_brl': system_cost,
        'monthly_savings_brl': round(monthly_savings, 2),
        'annual_savings_brl': round(annual_savings, 2),
        'simple_payback_years': round(simple_payback_years, 2),
        'discounted_payback_years': discounted_payback_years,
        'npv_brl': round(npv, 2),
        'tir_percent': round(tir * 100, 2) if tir else None,
        'total_savings_25_years_brl': round(sum(cash_flow[1:]), 2),
        'electricity_tariff_brl_kwh': electricity_tariff,
        'inflation_rate_percent': inflation_rate * 100,
        'discount_rate_percent': discount_rate * 100
    }

def validate_system_compatibility(modules_data, inverters_data):
    """
    Validação de compatibilidade entre módulos e inversores
    
    Args:
        modules_data: Lista de dicionários com dados dos módulos
        inverters_data: Lista de dicionários com dados dos inversores
    
    Returns:
        dict: Resultado da validação
    """
    
    total_module_power = sum(m.get('quantity', 0) * m.get('power', 0) for m in modules_data)
    total_inverter_power = sum(i.get('quantity', 0) * i.get('power', 0) for i in inverters_data)
    
    # Relação de potência (deve estar entre 1.1 e 1.3)
    power_ratio = total_module_power / total_inverter_power if total_inverter_power > 0 else 0
    
    warnings = []
    errors = []
    
    # Verificações de compatibilidade
    if power_ratio < 1.0:
        errors.append("Potência dos inversores maior que dos módulos")
    elif power_ratio > 1.4:
        warnings.append("Sobredimensionamento excessivo dos módulos (>140%)")
    elif power_ratio < 1.1:
        warnings.append("Subdimensionamento dos módulos (<110%)")
    
    # Verificar tensão (assumindo valores típicos)
    for module in modules_data:
        voc = 45  # Tensão de circuito aberto típica (V)
        vmpp = 37  # Tensão de máxima potência típica (V)
        
        # Número de módulos em série (assumindo string típica)
        modules_per_string = 10
        
        string_voc = voc * modules_per_string
        string_vmpp = vmpp * modules_per_string
        
        # Verificar limites do inversor (valores típicos)
        inverter_max_voltage = 1000  # V
        inverter_mppt_min = 200  # V
        inverter_mppt_max = 800  # V
        
        if string_voc > inverter_max_voltage:
            errors.append(f"Tensão de string ({string_voc}V) excede limite do inversor ({inverter_max_voltage}V)")
        
        if string_vmpp < inverter_mppt_min:
            warnings.append(f"Tensão MPPT ({string_vmpp}V) abaixo do mínimo ({inverter_mppt_min}V)")
        
        if string_vmpp > inverter_mppt_max:
            warnings.append(f"Tensão MPPT ({string_vmpp}V) acima do máximo ({inverter_mppt_max}V)")
    
    compatibility_status = "OK"
    if errors:
        compatibility_status = "ERRO"
    elif warnings:
        compatibility_status = "ATENÇÃO"
    
    return {
        'status': compatibility_status,
        'power_ratio': round(power_ratio, 2),
        'total_module_power_w': total_module_power,
        'total_inverter_power_w': total_inverter_power,
        'warnings': warnings,
        'errors': errors,
        'recommended_power_ratio': '1.1 - 1.3'
    }

# Exemplo de uso
if __name__ == "__main__":
    # Dados de exemplo
    modules = [
        {'quantity': 10, 'power': 450, 'model': 'Módulo 450W'},
        {'quantity': 5, 'power': 400, 'model': 'Módulo 400W'}
    ]
    
    inverters = [
        {'quantity': 1, 'power': 5000, 'model': 'Inversor 5kW'}
    ]
    
    # Testes dos cálculos
    print("=== Cálculo de Cabos ===")
    cable_calc = calculate_cable_section_advanced(6500, 220, 30)
    print(f"Seção recomendada: {cable_calc['recommended_section_mm2']} mm²")
    print(f"Queda de tensão: {cable_calc['voltage_drop_percent']}%")
    
    print("\n=== Dispositivos de Proteção ===")
    protection = calculate_protection_devices_advanced(6500, 220)
    print(f"Disjuntor AC: {protection['ac_breaker_a']}A")
    print(f"DPS: {protection['dps_class']} - {protection['dps_voltage']}")
    
    print("\n=== Geração de Energia ===")
    generation = calculate_energy_generation(modules)
    print(f"Geração mensal: {generation['monthly_generation_kwh']} kWh")
    print(f"Geração anual: {generation['annual_generation_kwh']} kWh")
    
    print("\n=== Análise Econômica ===")
    economics = calculate_economic_analysis(35000, generation['monthly_generation_kwh'])
    print(f"Payback simples: {economics['simple_payback_years']} anos")
    print(f"VPL: R$ {economics['npv_brl']:,.2f}")
    print(f"TIR: {economics['tir_percent']}%")
    
    print("\n=== Compatibilidade do Sistema ===")
    compatibility = validate_system_compatibility(modules, inverters)
    print(f"Status: {compatibility['status']}")
    print(f"Relação de potência: {compatibility['power_ratio']}")
    if compatibility['warnings']:
        print(f"Avisos: {compatibility['warnings']}")

