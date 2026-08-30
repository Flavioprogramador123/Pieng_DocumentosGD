# Integração de Cálculos e Tabelas nos Templates

## Visão Geral

O sistema Automação Equatorial possui pipeline completo de **cálculos técnicos automatizados** que são inseridos nos templates DOCX/XLSX via tokens `{{TOKEN}}`.

---

## Arquitetura de Integração

### Fluxo de Dados

```
Formulário Web
    ↓
backend/api_server.py → create_txt_data()
    ↓
backend/token_enrichment.py → enrich_normalized_payload()
    ↓
backend/system_calculations.py → calculate_technical_parameters()
    ↓
backend/demand_table.py → generate_demand_table()
    ↓
backend/gerar_documentos.py → preencher_template()
    ↓
Templates DOCX/XLSX com {{TOKENS}} preenchidos
```

---

## Módulos de Cálculo

### 1. **system_calculations.py** — Cálculos Completos do Sistema

**Função Principal**: `calculate_technical_parameters(modules, inverters, context)`

**Entrada**:
- `modules`: Lista de módulos fotovoltaicos (W)
- `inverters`: Lista de inversores (kW)
- `context`: Dados do cliente, UC, técnicos

**Saída** (tokens gerados):
```python
{
    'total_module_power_kw': 10.5,              # POTENCIA_TOTAL_INSTALADA
    'total_inverter_power_kw': 10.0,            # POTENCIA_INVERSOR_TOTAL
    'relacao_modulo_inversor': 1.05,            # —
    'estimated_monthly_generation': 1500,        # —
    'estimated_annual_generation': 18000,        # —
    'voltage_v': 220,                            # TENSAO_ATENDIMENTO
    'corrente_ac_a': 45.5,                       # CORRENTE_ENTRADA
    'disjuntor_recomendado_a': 63,               # DISJUNTOR_ENTRADA
    'cable_section_cc': '10mm²',                 # BITOLA_CABO_CC
    'cable_section_ca': '16mm²',                 # BITOLA_CABO_CA
    'dc_strings': {                              # Análise de strings CC
        'topology': 'string',
        'modules_per_string': 12,
        'string_voc_v': 550.0,
        'string_isc_a': 12.5,
        'isc_design_a': 15.6,                    # Isc × 1,25 (NR10)
    },
    'demand_table': { ... }                      # Tabela de demanda
}
```

**Recursos**:
- ✅ Cálculo de tensão por UF (GO: 380V trifásico)
- ✅ Análise de strings CC (V série, I paralelo)
- ✅ Dimensionamento de cabos e disjuntores
- ✅ Geração estimada (mensal/anual) com HSP
- ✅ Compatibilidade módulo/inversor (1,10–1,30)

---

### 2. **demand_table.py** — Tabela de Levantamento de Carga

**Função Principal**: `generate_demand_table(target_kw, classe, client_name, uc, notes, prefer_ai)`

**Entrada**:
- `target_kw`: Demanda-alvo do projeto (ex: 20 kW)
- `classe`: `'RESIDENCIAL'` ou `'INDUSTRIAL'`
- `prefer_ai`: `True` para usar Gemini AI

**Saída** (tabela formatada):
```python
{
    'memorial_text': """
Demanda-alvo de referência: 20,00 kW
Cliente: João Silva | UC: 12345678 | Classe: INDUSTRIAL

Item Descrição                                  Pot.W  Qtd  CI kW  FP   CI kVA  FD   D kW   D kVA
-----------------------------------------------------------------------------------------------------------
1    Iluminação industrial                      500    4    2,00   0,95 2,11    100% 2,00   2,11
2    Tomadas de uso geral                       750    4    3,00   0,90 3,33    80%  2,40   2,67
3    Compressor de ar industrial                7500   1    7,50   0,85 8,82    80%  6,00   7,06
4    Bomba/motor de processo                    5500   1    5,50   0,85 6,47    80%  4,40   5,18
5    Máquina de solda                           5000   1    5,00   0,80 6,25    80%  4,00   5,00
6    Escritório, informática e apoio            2000   1    2,00   0,95 2,11    60%  1,20   1,27
-----------------------------------------------------------------------------------------------------------
TOTAL Demanda de projeto — conferir no local   —      —    25,00  —    29,09   —    20,00  23,29

Observação: rascunho de referência gerado automaticamente.
Substituir cargas, FP e FD pelos valores reais levantados in loco antes do protocolo.
Fonte: modelo escalado por demanda-alvo informada.
    """,
    'rows': [ ... ],    # Dados estruturados para API
    'totals': {
        'd_kw': 20.0,
        'd_kva': 23.29
    }
}
```

**Recursos**:
- ✅ Templates RESIDENCIAL e INDUSTRIAL pré-carregados
- ✅ Escalonamento automático para atingir demanda-alvo
- ✅ IA opcional (Gemini) para sugestão de cargas personalizadas
- ✅ Formatação brasileira (vírgula como separador decimal)
- ✅ Cálculos: CI (kW/kVA), D (kW/kVA), FP, FD

---

### 3. **string_calculations.py** — Análise de Strings CC

**Função Principal**: `analyze_dc_strings(modules, inverters, technical)`

**Recursos**:
- ✅ Detecção de topologia: microinversor, string ou paralelo
- ✅ Cálculo de Voc série (V somam em série)
- ✅ Cálculo de Isc (I não soma — mesmo valor da string)
- ✅ Isc de projeto = Isc × 1,25 (norma)
- ✅ Validação de compatibilidade MPPT

**Exemplo de Saída**:
```python
{
    'topology': 'string',
    'modules_per_string': 14,
    'total_modules': 28,
    'total_strings': 2,
    'string_voc_v': 644.0,        # 14 módulos × 46V
    'string_isc_a': 13.5,         # Isc de 1 módulo
    'isc_design_a': 16.9,         # 13,5 × 1,25
    'status': 'OK',
    'messages': ['Strings dentro da faixa MPPT do inversor']
}
```

---

### 4. **advanced_calculations.py** — Cálculos Avançados

**Funções**:
- `calculate_energy_generation(modules)` — Geração mensal/anual
- `calculate_cable_section_advanced(power_w, voltage)` — Seção de cabos (mm²)
- `calculate_protection_devices_advanced(power_w, voltage, system_type)` — Disjuntores e DPS

---

## Token Enrichment Pipeline

### **token_enrichment.py** — Enriquecimento Antes da Geração

**Função Principal**: `enrich_normalized_payload(normalized)`

**Passos**:
1. **Padrão de Entrada** — Consulta catálogo SQLite por UF/ligação
2. **Módulos** — Preenche Voc, Isc, dimensões do catálogo
3. **Inversores** — Preenche MPPT, THD, specs técnicas
4. **Defaults Residenciais** — Disjuntor 63A, DPS Classe II, cabos
5. **Tabela de Demanda** — Gera automaticamente se `demanda_alvo_kw` informado

**Código**:
```python
def _ensure_demand_table(normalized: dict) -> None:
    tec = normalized.setdefault('dados_tecnicos', {})
    if not _empty(tec.get('tabela_demanda_text')):
        return  # Já preenchido
    alvo = tec.get('demanda_alvo_kw')
    if _empty(alvo):
        return  # Sem demanda-alvo

    from demand_table import generate_demand_table
    cliente = normalized.get('cliente') or {}
    uc = normalized.get('unidade_consumidora') or {}

    table = generate_demand_table(
        target_kw=float(str(alvo).replace(',', '.')),
        classe=uc.get('classe') or 'RESIDENCIAL',
        client_name=cliente.get('nome') or '',
        uc=uc.get('numero') or '',
        notes=tec.get('demanda_notas') or '',
    )
    tec['tabela_demanda_text'] = table.get('memorial_text') or ''
```

---

## Integração no Template DOCX

### **Memorial Descritivo** — `MEMORIAL_DESCRITIVO_marcadores.docx`

**Token**: `{{TABELA_DEMANDA}}`

**Localização**: Abaixo do título **"Tabela 1 – Levantamento de Carga"**

**Processamento** (`backend/gerar_documentos.py`):
```python
if values.get('TABELA_DEMANDA'):
    # Substituir marcador {{NL}} por quebra de linha real
    values['TABELA_DEMANDA'] = values['TABELA_DEMANDA'].replace(' {{NL}} ', '\n')
```

**Fluxo**:
1. Frontend envia `demanda_alvo_kw: 20`
2. `token_enrichment.py` detecta campo vazio `tabela_demanda_text`
3. Chama `generate_demand_table(20, 'INDUSTRIAL', ...)`
4. Gera texto formatado com tabela ASCII
5. `create_txt_data()` converte para formato TXT: `"Tabela de Demanda: linha1 {{NL}} linha2 {{NL}} ..."`
6. `gerar_documentos.py` substitui `{{NL}}` por `\n`
7. Template DOCX recebe texto com quebras de linha reais

**Exemplo no Template**:
```
4. LEVANTAMENTO DE CARGA

Tabela 1 – Levantamento de Carga

{{TABELA_DEMANDA}}

5. DIMENSIONAMENTO
```

**Resultado Final**:
```
4. LEVANTAMENTO DE CARGA

Tabela 1 – Levantamento de Carga

Demanda-alvo de referência: 20,00 kW
Cliente: João Silva | UC: 12345678 | Classe: INDUSTRIAL

Item Descrição                                  Pot.W  Qtd  CI kW  FP   CI kVA  FD   D kW   D kVA
-----------------------------------------------------------------------------------------------------------
1    Iluminação industrial                      500    4    2,00   0,95 2,11    100% 2,00   2,11
...
TOTAL Demanda de projeto — conferir no local   —      —    25,00  —    29,09   —    20,00  23,29

Observação: rascunho de referência gerado automaticamente.

5. DIMENSIONAMENTO
```

---

## Outros Tokens de Cálculos

### Tokens Automáticos no Memorial/Procuração

| Token | Origem | Exemplo |
|-------|--------|---------|
| `{{POTENCIA_TOTAL_INSTALADA}}` | `total_module_power_kw` | `10,50 kWp` |
| `{{POTENCIA_INVERSOR_TOTAL}}` | `total_inverter_power_kw` | `10,00 kW` |
| `{{TENSAO_ATENDIMENTO}}` | `voltage_v` (resolve_ac_voltage) | `220V` (GO: 380V) |
| `{{CORRENTE_ENTRADA}}` | `corrente_ac_a` | `45,5 A` |
| `{{DISJUNTOR_ENTRADA}}` | `disjuntor_recomendado_a` | `63 A` |
| `{{BITOLA_CABO_CC}}` | `cable_section_cc` | `10mm²` |
| `{{BITOLA_CABO_CA}}` | `cable_section_ca` | `16mm²` |
| `{{TABELA_DEMANDA}}` | `memorial_text` (demand_table) | Tabela completa |

---

## Como Adicionar Novo Cálculo/Tabela

### Passo 1: Criar Função de Cálculo

**Arquivo**: `backend/custom_calculation.py`
```python
def calculate_new_feature(param1, param2):
    """Descrição do cálculo."""
    result = param1 * param2 / 1000
    return {
        'value': result,
        'formatted': f"{result:.2f} kW",
        'token': 'NOVO_CALCULO'
    }
```

### Passo 2: Integrar no Pipeline

**Editar**: `backend/token_enrichment.py`
```python
from custom_calculation import calculate_new_feature

def enrich_normalized_payload(normalized: dict) -> dict:
    # ... código existente ...

    # Novo cálculo
    tec = result.get('dados_tecnicos') or {}
    if tec.get('param1') and tec.get('param2'):
        calc = calculate_new_feature(tec['param1'], tec['param2'])
        tec['novo_campo'] = calc['formatted']

    return result
```

### Passo 3: Mapear para TXT

**Editar**: `backend/api_server.py` → `create_txt_data()`
```python
tecnicos = data.get('dados_tecnicos', {})
if tecnicos.get('novo_campo'):
    lines.append(f"Novo Cálculo: {tecnicos['novo_campo']}")
```

### Passo 4: Adicionar Alias no Gerador

**Editar**: `backend/gerar_documentos.py` → `LABEL_ALIASES`
```python
LABEL_ALIASES = {
    # ... aliases existentes ...
    'novo cálculo': 'NOVO_CALCULO',
}
```

### Passo 5: Inserir Token no Template

**Editar**: `templates/MEMORIAL_DESCRITIVO_marcadores.docx`
```
O valor calculado é {{NOVO_CALCULO}}.
```

---

## Validação e Testes

### Testar Localmente

1. **Iniciar sistema**:
```batch
iniciar.bat
```

2. **Preencher formulário** com:
   - Módulos: 20 × 550W
   - Inversor: 1 × 10kW
   - Demanda-alvo: 20 kW

3. **Gerar documentos**

4. **Verificar tokens no Memorial**:
   - Abrir `MEMORIAL_DESCRITIVO_*.docx`
   - Buscar por `{{TABELA_DEMANDA}}` → deve estar preenchido
   - Verificar outros tokens calculados

---

## Troubleshooting

### ❌ Token `{{TABELA_DEMANDA}}` Vazio

**Causa**: Campo `demanda_alvo_kw` não informado

**Solução**:
1. Preencher campo "Demanda Alvo (kW)" na aba **Técnicos**
2. Ou adicionar via YAML: `dados_tecnicos.demanda_alvo_kw: 20`

### ❌ Tabela de Demanda com Quebras de Linha Incorretas

**Causa**: Marcador `{{NL}}` não sendo substituído

**Solução**:
- Verificar `gerar_documentos.py` linha 442-443:
```python
if values.get('TABELA_DEMANDA'):
    values['TABELA_DEMANDA'] = values['TABELA_DEMANDA'].replace(' {{NL}} ', '\n')
```

### ❌ Cálculos com Valores Zerados

**Causa**: Unidades incorretas (módulo em kW em vez de W)

**Solução**:
- Módulos: **SEMPRE em Watts (W)** — ex: 550
- Inversores: **SEMPRE em kilowatts (kW)** — ex: 10

---

## Roadmap de Melhorias

- [ ] Adicionar mais templates de demanda (comercial, rural)
- [ ] Integrar cálculo de payback e ROI
- [ ] Tabela de geração mensal (12 meses) no memorial
- [ ] Gráfico de geração (inserir imagem no DOCX)
- [ ] Validação de compatibilidade MPPT com alertas visuais
- [ ] Exportar cálculos para JSON/PDF separado

---

## Referências

- **Templates**: `templates/MEMORIAL_DESCRITIVO_marcadores.docx`
- **Módulo Principal**: `backend/system_calculations.py`
- **Tabela de Demanda**: `backend/demand_table.py`
- **Enrichment**: `backend/token_enrichment.py`
- **Gerador**: `backend/gerar_documentos.py`

---

**Última Atualização**: 2026-08-28 — v0.5.0
