# Enrichment Automático de Equipamentos

Documentação do preenchimento automático de especificações técnicas a partir do catálogo SQLite.

---

## O Que é Enrichment?

O sistema **enriquece** automaticamente os dados de módulos e inversores quando você importa TXT ou YAML, preenchendo **TODOS os campos técnicos** a partir do catálogo SQLite local.

### Antes vs Depois

**ANTES** (você digitava manualmente):
```yaml
Inversor:
  Fabricante: DEYE
  Modelo: MICRO INVERSOR DEYE-S2.25K-G4 220V
  Potência: 2.25kW
  # Campos vazios:
  # - num_mppt: ?
  # - mppt_min: ?
  # - mppt_max: ?
  # - tipo_inversor: ?
```

**DEPOIS** (sistema preenche automaticamente):
```yaml
Inversor:
  Fabricante: DEYE
  Modelo: MICRO INVERSOR DEYE-S2.25K-G4 220V
  Potência: 2.25kW
  num_mppt: 4              ← Preenchido automaticamente!
  mppt_min: 25V            ← Preenchido automaticamente!
  mppt_max: 55V            ← Preenchido automaticamente!
  tipo_inversor: MICRO     ← Preenchido automaticamente!
  tensao_nominal: 220V     ← Preenchido automaticamente!
  eficiencia: 96.5%        ← Preenchido automaticamente!
```

---

## Quando Acontece o Enrichment?

O enrichment é executado **AUTOMATICAMENTE** em 3 momentos:

### 1. Importação de TXT (aba TXT)
```
Usuário cola TXT → /api/analyze-text → Parser → enrich_normalized_payload() → Dados enriquecidos
```

### 2. Importação de YAML
```
Usuário importa YAML → /api/import-yaml → import_yaml_project() → enrich_normalized_payload() → Dados enriquecidos
```

### 3. Geração de documentos
```
Usuário clica "Gerar" → create_txt_data() → enrich_normalized_payload() → Documentos com dados completos
```

---

## Campos Preenchidos Automaticamente

### Módulos Fotovoltaicos

| Campo | Exemplo |
|-------|---------|
| `fabricante` | RENE PV |
| `modelo` | 620W Bifacial |
| `potencia` | 620.0 Wp |
| `voc` | 47.98 V |
| `isc` | 16.3 A |
| `vmpp` | 40.39 V |
| `impp` | 15.35 A |
| `eficiencia` | 22.9% |
| `comprimento_m` | 2.465 m |
| `largura_m` | 1.134 m |
| `area_modulo` | 2.795 m² |

### Inversores

| Campo | Exemplo |
|-------|---------|
| `fabricante` | DEYE |
| `modelo` | MICRO INVERSOR DEYE-S2.25K-G4 220V |
| `potencia` | 2.25 kW |
| `tipo_inversor` | MICRO |
| **`num_mppt`** | **4** ← Campo crítico! |
| `mppt_min` | 25.0 V |
| `mppt_max` | 55.0 V |
| `tensao_nominal` | 220.0 V |
| `corrente_nominal` | 10.2 A |
| `eficiencia` | 96.5% |

---

## Estratégia de Busca Inteligente (3 Camadas)

O sistema tenta 3 estratégias diferentes antes de desistir:

### Tier 1: Match Exato (Fabricante + Modelo)
```python
Entrada: fabricante='DEYE', modelo='MICRO INVERSOR DEYE-S2.25K-G4 220V'
Busca: LOWER(fabricante) LIKE '%deye%' AND LOWER(modelo) LIKE '%micro inversor deye-s2.25k-g4%'
Resultado: ✅ ENCONTRADO
```

### Tier 2: Match por Potência Exata (Fabricante + Potência)
```python
Entrada: fabricante='DEYE', potencia_kw=2.25 (modelo vazio)
Busca: LOWER(fabricante) LIKE '%deye%' AND potencia_kw = 2.25
Resultado: ✅ ENCONTRADO
```

### Tier 3: Match com Tolerância (±5% módulos, ±10% inversores)
```python
Entrada: fabricante='DEYE', potencia_kw=2.1 (aproximado)
Busca: LOWER(fabricante) LIKE '%deye%' AND potencia_kw BETWEEN 2.025 AND 2.475 (±10%)
Resultado: ✅ ENCONTRADO (mais próximo de 2.1 = DEYE 2.25kW)
```

### Se Nenhuma Camada Encontrar
```
Fallback → Gemini API (último recurso)
```

---

## Exemplo Prático: TXT Importado

### TXT Original (colado pelo usuário)
```
INVERSOR: MICRO INVERSOR DEYE-S2.25K-G4 220V
POTENCIA INVERSOR: 2.25kW
QUANTIDADE: 10
```

### Dados Parseados (após /api/analyze-text)
```json
{
  "inversores": [
    {
      "fabricante": "DEYE",
      "modelo": "MICRO INVERSOR DEYE-S2.25K-G4 220V",
      "potencia": 2.25,
      "quantidade": 10
    }
  ]
}
```

### Dados Enriquecidos (após enrich_normalized_payload)
```json
{
  "inversores": [
    {
      "fabricante": "DEYE",
      "modelo": "MICRO INVERSOR DEYE-S2.25K-G4 220V",
      "potencia": 2.25,
      "quantidade": 10,
      "num_mppt": 4,
      "mppt_min": 25.0,
      "mppt_max": 55.0,
      "tipo_inversor": "MICRO",
      "tensao_nominal": 220.0,
      "corrente_nominal": 10.2,
      "eficiencia": 96.5
    }
  ]
}
```

---

## Fluxograma Completo

```
┌─────────────────────────────────────────────────────────────┐
│ Usuário cola TXT ou importa YAML                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ /api/analyze-text ou /api/import-yaml                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ normalize_form_payload()                                     │
│ - Extrai modulos[] e inversores[]                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ enrich_normalized_payload()                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│ Para cada MÓDULO │            │ Para cada INVERSOR│
└────────┬─────────┘            └────────┬─────────┘
         │                                │
         ▼                                ▼
┌────────────────────────┐      ┌────────────────────────┐
│_fill_module_from_catalog│    │_fill_inverter_from_catalog│
└────────┬───────────────┘      └────────┬───────────────┘
         │                                │
         ▼                                ▼
┌────────────────────────────────────────────────────────────┐
│ find_module_by_name_or_power() / find_inverter_by_name_or_power()│
│                                                             │
│ Tier 1: Fabricante + Modelo (exato)                       │
│    │                                                        │
│    ▼ Não encontrou?                                        │
│ Tier 2: Fabricante + Potência (exata)                     │
│    │                                                        │
│    ▼ Não encontrou?                                        │
│ Tier 3: Fabricante + Potência (±tolerância)               │
│    │                                                        │
│    ▼ Encontrou!                                            │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ catalog_module_to_specs() / catalog_inverter_to_specs()     │
│ - Retorna dict com TODOS os campos técnicos                 │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Preencher campos vazios do equipamento                       │
│ - voc, isc, vmpp, impp, eficiencia (módulos)                │
│ - num_mppt, mppt_min, mppt_max, tipo_inversor (inversores)  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Retornar dados ENRIQUECIDOS para frontend                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Código-Fonte Relevante

### Backend
- [backend/token_enrichment.py](../backend/token_enrichment.py) — Pipeline principal de enrichment
- [backend/catalog_db.py](../backend/catalog_db.py) — Funções de busca inteligente
- [backend/equipment_enrichment.py](../backend/equipment_enrichment.py) — Enrichment via IA (fallback)

### Endpoints Atualizados
- `POST /api/analyze-text` — Agora enriquece automaticamente
- `POST /api/import-yaml` — Já enriquecia (via import_yaml_project)
- `POST /api/catalog/find-module` — Busca manual de módulo
- `POST /api/catalog/find-inverter` — Busca manual de inversor

---

## Verificando se Enrichment Funcionou

### No Console do Backend
```bash
cd backend
python test_enrichment.py
```

**Saída esperada**:
```
[OK] Módulo enriquecido com sucesso (Voc e Isc preenchidos)
[OK] Inversor enriquecido com sucesso (num_mppt=4 preenchido)
[OK] TESTE PASSOU - Enrichment funcionando corretamente!
```

### Via API (curl)
```bash
curl -X POST http://localhost:5000/api/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text": "INVERSOR: MICRO INVERSOR DEYE-S2.25K-G4 220V\nPOTENCIA: 2.25kW"}'
```

**Verifique na resposta**:
```json
{
  "success": true,
  "catalog_enriched": true,
  "data": {
    "inversores": [{
      "num_mppt": 4,
      "mppt_min": 25.0,
      "mppt_max": 55.0,
      ...
    }]
  }
}
```

---

## Troubleshooting

### Problema: Campos não são preenchidos

**Causa 1**: Equipamento não está no catálogo SQLite
```bash
# Verificar se está no banco
cd backend
python -c "from catalog_db import list_table; print(list_table('inverters', limit=10))"
```

**Solução**: Importar YAML de inversores/módulos
```bash
# Via frontend: aba Catálogo → Importar Módulos/Inversores YAML
# Ou via API:
curl -X POST http://localhost:5000/api/catalog/import-inversores-yaml
```

**Causa 2**: Nome/modelo não bate (tolerância excedida)
```
Catálogo: "DEYE MICRO INVERSOR S2.25K"
TXT/YAML: "DEYE S2.25K-G4"
→ Match falha (modelos diferentes)
```

**Solução**: Ajustar nome no TXT/YAML ou adicionar variação no catálogo

**Causa 3**: Frontend não está exibindo os dados
```
Backend enriquece → Frontend recebe → Mas não renderiza no formulário
```

**Solução**: Verificar componente React que renderiza equipamentos (próximo passo)

---

## Próximos Passos

### Para o Desenvolvedor Frontend
1. Verificar se `EquipmentForm.jsx` está renderizando campos como `num_mppt`
2. Adicionar feedback visual quando dados são enriquecidos
3. Mostrar badge "📂 Do Catálogo" quando equipamento foi encontrado no SQLite

### Para o Usuário Final
1. Cole TXT ou importe YAML normalmente
2. Sistema preenche campos automaticamente
3. Revise dados e ajuste se necessário
4. Clique em "Calcular" para prosseguir

---

**Versão**: 0.5.3
**Data**: 2026-08-28
**Status**: ✅ Funcional (backend) | ⚠️ Frontend precisa exibir dados enriquecidos
