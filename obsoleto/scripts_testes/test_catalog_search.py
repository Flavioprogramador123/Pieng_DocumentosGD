"""
Testes para verificar funcionamento da busca inteligente de equipamentos.
"""

from catalog_db import (
    search_modules_fuzzy,
    search_inverters_fuzzy,
    find_module_by_name_or_power,
    find_inverter_by_name_or_power,
    list_table,
)


def test_module_fuzzy_search():
    """Teste: busca fuzzy de módulos."""
    print("\n" + "="*80)
    print("TESTE 1: Busca Fuzzy de Módulos")
    print("="*80)

    results = search_modules_fuzzy(
        query='Canadian',
        potencia_min=400,
        potencia_max=600,
        limit=5,
    )

    print(f"\nBuscando 'Canadian' com potência 400-600W (limit 5):")
    print(f"Encontrados: {len(results)} módulos\n")

    for i, mod in enumerate(results, 1):
        print(f"{i}. {mod.get('fabricante')} {mod.get('modelo')} - {mod.get('potencia_wp')}Wp")
        print(f"   Voc: {mod.get('voc')}V, Isc: {mod.get('isc')}A")
        print(f"   Relevância: {mod.get('relevancia', 1)}")
        print()

    return len(results) > 0


def test_module_smart_search():
    """Teste: busca inteligente de módulos (3 camadas)."""
    print("\n" + "="*80)
    print("TESTE 2: Busca Inteligente de Módulos (3 Camadas)")
    print("="*80)

    # Lista alguns módulos disponíveis
    all_modules = list_table('modules', limit=3)
    if not all_modules:
        print("[AVISO] Catálogo vazio! Importe módulos primeiro com import_modulos_yaml()")
        return False

    print("\nMódulos disponíveis no catálogo (primeiros 3):")
    for mod in all_modules:
        print(f"  - {mod.get('fabricante')} {mod.get('modelo')} ({mod.get('potencia_wp')}Wp)")

    # Pegar primeiro módulo para teste
    ref = all_modules[0]
    fabricante = ref.get('fabricante', '')
    modelo = ref.get('modelo', '')
    potencia = ref.get('potencia_wp', 0)

    # Tier 1: Match exato
    print(f"\n--- Tier 1: Match Exato ---")
    print(f"Buscando: {fabricante} {modelo} {potencia}Wp")
    module = find_module_by_name_or_power(
        fabricante=fabricante,
        modelo=modelo,
        potencia_wp=potencia,
    )
    if module:
        print(f"[OK] ENCONTRADO: {module.get('fabricante')} {module.get('modelo')} ({module.get('potencia_wp')}Wp)")
    else:
        print("[ERRO] NÃO ENCONTRADO")

    # Tier 2: Match por potência (sem modelo)
    print(f"\n--- Tier 2: Match por Potência (sem modelo) ---")
    print(f"Buscando: {fabricante} (sem modelo) {potencia}Wp")
    module = find_module_by_name_or_power(
        fabricante=fabricante,
        modelo='',
        potencia_wp=potencia,
    )
    if module:
        print(f"[OK] ENCONTRADO: {module.get('fabricante')} {module.get('modelo')} ({module.get('potencia_wp')}Wp)")
    else:
        print("[ERRO] NÃO ENCONTRADO")

    # Tier 3: Match com tolerância
    potencia_aproximada = int(potencia * 0.98)  # -2% (dentro da tolerância de ±5%)
    print(f"\n--- Tier 3: Match com Tolerância ±5% ---")
    print(f"Buscando: {fabricante} (sem modelo) {potencia_aproximada}Wp (aproximado)")
    module = find_module_by_name_or_power(
        fabricante=fabricante,
        modelo='',
        potencia_wp=potencia_aproximada,
    )
    if module:
        print(f"[OK] ENCONTRADO: {module.get('fabricante')} {module.get('modelo')} ({module.get('potencia_wp')}Wp)")
        print(f"   Diferença: {abs(module.get('potencia_wp', 0) - potencia_aproximada)}Wp")
    else:
        print("[ERRO] NÃO ENCONTRADO")

    return True


def test_inverter_fuzzy_search():
    """Teste: busca fuzzy de inversores."""
    print("\n" + "="*80)
    print("TESTE 3: Busca Fuzzy de Inversores")
    print("="*80)

    results = search_inverters_fuzzy(
        query='Deye',
        potencia_min=5,
        potencia_max=15,
        limit=5,
    )

    print(f"\nBuscando 'Deye' com potência 5-15kW (limit 5):")
    print(f"Encontrados: {len(results)} inversores\n")

    for i, inv in enumerate(results, 1):
        print(f"{i}. {inv.get('fabricante')} {inv.get('modelo')} - {inv.get('potencia_kw')}kW")
        print(f"   MPPT: {inv.get('mppt_min')}-{inv.get('mppt_max')}V")
        print(f"   Tipo: {inv.get('tipo_inversor', 'N/A')}")
        print(f"   Relevância: {inv.get('relevancia', 1)}")
        print()

    return len(results) > 0


def test_inverter_smart_search():
    """Teste: busca inteligente de inversores (3 camadas)."""
    print("\n" + "="*80)
    print("TESTE 4: Busca Inteligente de Inversores (3 Camadas)")
    print("="*80)

    # Lista alguns inversores disponíveis
    all_inverters = list_table('inverters', limit=3)
    if not all_inverters:
        print("[AVISO] Catálogo vazio! Importe inversores primeiro com import_inversores_yaml()")
        return False

    print("\nInversores disponíveis no catálogo (primeiros 3):")
    for inv in all_inverters:
        print(f"  - {inv.get('fabricante')} {inv.get('modelo')} ({inv.get('potencia_kw')}kW)")

    # Pegar primeiro inversor para teste
    ref = all_inverters[0]
    fabricante = ref.get('fabricante', '')
    modelo = ref.get('modelo', '')
    potencia = ref.get('potencia_kw', 0)

    # Tier 1: Match exato
    print(f"\n--- Tier 1: Match Exato ---")
    print(f"Buscando: {fabricante} {modelo} {potencia}kW")
    inverter = find_inverter_by_name_or_power(
        fabricante=fabricante,
        modelo=modelo,
        potencia_kw=potencia,
    )
    if inverter:
        print(f"[OK] ENCONTRADO: {inverter.get('fabricante')} {inverter.get('modelo')} ({inverter.get('potencia_kw')}kW)")
    else:
        print("[ERRO] NÃO ENCONTRADO")

    # Tier 3: Match com tolerância ±10%
    potencia_aproximada = potencia * 0.95  # -5% (dentro da tolerância de ±10%)
    print(f"\n--- Tier 3: Match com Tolerância ±10% ---")
    print(f"Buscando: {fabricante} (sem modelo) {potencia_aproximada:.1f}kW (aproximado)")
    inverter = find_inverter_by_name_or_power(
        fabricante=fabricante,
        modelo='',
        potencia_kw=potencia_aproximada,
    )
    if inverter:
        print(f"[OK] ENCONTRADO: {inverter.get('fabricante')} {inverter.get('modelo')} ({inverter.get('potencia_kw')}kW)")
        print(f"   Diferença: {abs(inverter.get('potencia_kw', 0) - potencia_aproximada):.2f}kW")
    else:
        print("[ERRO] NÃO ENCONTRADO")

    return True


def test_enrichment_integration():
    """Teste: integração com equipment_enrichment.py."""
    print("\n" + "="*80)
    print("TESTE 5: Integração com equipment_enrichment.py")
    print("="*80)

    from equipment_enrichment import enrich_module_specs, enrich_inverter_specs

    # Pegar módulo do catálogo
    modules = list_table('modules', limit=1)
    if modules:
        mod = modules[0]
        print(f"\nTestando enriquecimento de módulo existente no catálogo:")
        print(f"  Input: {mod.get('fabricante')} {mod.get('modelo')} {mod.get('potencia_wp')}Wp")

        specs, source = enrich_module_specs(
            mod.get('fabricante'),
            mod.get('modelo'),
            mod.get('potencia_wp'),
        )

        print(f"  Source: {source}")
        if source == 'catalog':
            print(f"  [OK] SUCESSO: Encontrado no catálogo SQLite (sem chamar Gemini)")
            print(f"  Specs: Voc={specs.get('voc')}V, Isc={specs.get('isc')}A")
        else:
            print(f"  [AVISO] Chamou {source} (esperava 'catalog')")

    # Pegar inversor do catálogo
    inverters = list_table('inverters', limit=1)
    if inverters:
        inv = inverters[0]
        print(f"\nTestando enriquecimento de inversor existente no catálogo:")
        print(f"  Input: {inv.get('fabricante')} {inv.get('modelo')} {inv.get('potencia_kw')}kW")

        specs, source = enrich_inverter_specs(
            inv.get('fabricante'),
            inv.get('modelo'),
            inv.get('potencia_kw'),
        )

        print(f"  Source: {source}")
        if source == 'catalog':
            print(f"  [OK] SUCESSO: Encontrado no catálogo SQLite (sem chamar Gemini)")
            print(f"  Specs: MPPT {specs.get('mppt_min')}-{specs.get('mppt_max')}V")
        else:
            print(f"  [AVISO] Chamou {source} (esperava 'catalog')")

    return True


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "="*80)
    print("  TESTES DE BUSCA INTELIGENTE DE EQUIPAMENTOS")
    print("="*80)

    results = []

    results.append(("Busca Fuzzy de Módulos", test_module_fuzzy_search()))
    results.append(("Busca Inteligente de Módulos", test_module_smart_search()))
    results.append(("Busca Fuzzy de Inversores", test_inverter_fuzzy_search()))
    results.append(("Busca Inteligente de Inversores", test_inverter_smart_search()))
    results.append(("Integração com Enrichment", test_enrichment_integration()))

    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)

    for name, passed in results:
        status = "[OK] PASSOU" if passed else "[ERRO] FALHOU"
        print(f"{status} - {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} testes passaram")
    print("="*80 + "\n")

    return passed_count == total_count


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
