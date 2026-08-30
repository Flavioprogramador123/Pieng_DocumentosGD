"""
Teste rápido para verificar enrichment de equipamentos do catálogo.
"""

from token_enrichment import enrich_normalized_payload

# Simular dados vindos do TXT/YAML (apenas com fabricante/modelo/potência)
# IMPORTANTE: enrich_normalized_payload espera modulos/inversores NO NÍVEL RAIZ
dados_minimos = {
    'modulos': [
        {
            'fabricante': 'RENE PV',
            'modelo': '620W Bifacial',
            'quantidade': 20,
            # Voc, Isc, etc VAZIOS - devem ser preenchidos pelo catálogo
        }
    ],
    'inversores': [
        {
            'fabricante': 'DEYE',
            'modelo': 'MICRO INVERSOR DEYE-S2.25K-G4 220V',
            'quantidade': 10,
            # num_mppt, mppt_min, mppt_max VAZIOS - devem ser preenchidos pelo catálogo
        }
    ],
    'dados_tecnicos': {}
}

print("="*80)
print("TESTE DE ENRICHMENT DE CATÁLOGO")
print("="*80)

print("\n--- DADOS ANTES DO ENRICHMENT ---")
print(f"Módulo: {dados_minimos['modulos'][0]}")
print(f"Inversor: {dados_minimos['inversores'][0]}")

# Enriquecer com catálogo
dados_enriquecidos = enrich_normalized_payload(dados_minimos)

print("\n--- DADOS DEPOIS DO ENRICHMENT ---")
modulo = dados_enriquecidos['modulos'][0]
inversor = dados_enriquecidos['inversores'][0]

print(f"\nMódulo enriquecido:")
print(f"  Fabricante: {modulo.get('fabricante')}")
print(f"  Modelo: {modulo.get('modelo')}")
print(f"  Potência: {modulo.get('potencia')}Wp")
print(f"  Voc: {modulo.get('voc')}V")
print(f"  Isc: {modulo.get('isc')}A")
print(f"  Vmpp: {modulo.get('vmpp')}V")
print(f"  Impp: {modulo.get('impp')}A")
print(f"  Eficiência: {modulo.get('eficiencia')}%")

print(f"\nInversor enriquecido:")
print(f"  Fabricante: {inversor.get('fabricante')}")
print(f"  Modelo: {inversor.get('modelo')}")
print(f"  Potência: {inversor.get('potencia')}kW")
print(f"  Tipo: {inversor.get('tipo_inversor')}")
print(f"  *** NUM_MPPT: {inversor.get('num_mppt')} ***")
print(f"  MPPT min: {inversor.get('mppt_min')}V")
print(f"  MPPT max: {inversor.get('mppt_max')}V")
print(f"  Tensão nominal: {inversor.get('tensao_nominal')}V")
print(f"  Eficiência: {inversor.get('eficiencia')}%")

# Verificação
print("\n" + "="*80)
print("VERIFICAÇÃO:")
print("="*80)

modulo_ok = bool(modulo.get('voc') and modulo.get('isc'))
inversor_ok = bool(inversor.get('num_mppt') and inversor.get('mppt_min'))

if modulo_ok:
    print("[OK] Módulo enriquecido com sucesso (Voc e Isc preenchidos)")
else:
    print("[ERRO] Módulo NÃO foi enriquecido (Voc/Isc vazios)")

if inversor_ok:
    print(f"[OK] Inversor enriquecido com sucesso (num_mppt={inversor.get('num_mppt')} preenchido)")
else:
    print("[ERRO] Inversor NÃO foi enriquecido (num_mppt vazio)")

if modulo_ok and inversor_ok:
    print("\n[OK] TESTE PASSOU - Enrichment funcionando corretamente!")
else:
    print("\n[ERRO] TESTE FALHOU - Enrichment nao esta preenchendo os campos")

print("="*80)
